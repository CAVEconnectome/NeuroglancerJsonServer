import datetime
import os
import zlib
import uuid

from datastoreflex import DatastoreFlex
from google.cloud import datastore
from cloudfiles import CloudFiles

HOME = os.path.expanduser("~")
MAX_JSON_SIZE = 52_428_800  # 50 x 1024 x 1024 bytes = ~50MB

# Setting environment wide credential path
if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
        HOME + "/.cloudvolume/secrets/google-secret.json"
    )


class JsonDataBase(object):
    def __init__(
        self,
        table_name,
        project_id=None,
        client=None,
        credentials=None,
        columns=("v2", "v1"),
    ):
        if client is not None:
            self._client = client
        else:
            assert project_id is not None
            self._client = DatastoreFlex(
                project=project_id, credentials=credentials, namespace=table_name
            )

        self._namespace = table_name
        self._columns = columns

    @property
    def client(self):
        return self._client

    @property
    def namespace(self):
        return self._namespace

    @property
    def project_id(self):
        return self.client.project

    @property
    def kind(self):
        return "ngl_json"

    @property
    def json_columns(self) -> tuple:
        """Tuple of column names in decreasing precedence for where JSONs are stored."""
        return self._columns

    def add_json(self, json_data, user_id, json_id=None, date=None):
        if json_id is None:
            key = self.client.key(self.kind, namespace=self.namespace)
        else:
            key = self.client.key(self.kind, json_id, namespace=self.namespace)

        try:
            entity = self.client.get(key)
        except:
            entity = None

        if entity is not None:
            raise Exception(f"[{self.namespace}][{key}][{json_id}] ID already exists.")

        entity = datastore.Entity(key, exclude_from_indexes=self.json_columns)

        # always put into the first column for new data
        # could play with different schemes here in the future
        json_bytes = zlib.compress(json_data)
        if len(json_bytes) > MAX_JSON_SIZE:
            raise ValueError(
                f"JSON data too large, must be compressible to <{MAX_JSON_SIZE} bytes."
            )
        entity[self.json_columns[0]] = json_bytes

        entity["access_counter"] = int(1)
        entity["user_id"] = user_id

        now = datetime.datetime.utcnow()
        if date is None:
            date = now

        entity["date"] = date
        entity["date_last"] = now

        self.client.put(entity)

        return entity.key.id

    def _find_json_column(self, entity: datastore.Entity):
        # look for the JSON data in decreasing order of precedence
        found_column = None
        for column in self.json_columns:
            if column in entity.keys():
                if entity.get(column) is None:
                    continue
                else:
                    found_column = column
                break

        return found_column

    def get_json(self, json_id, decompress=True):
        key = self.client.key(self.kind, json_id, namespace=self.namespace)

        entity = self.client.get(key)

        found_column = self._find_json_column(entity)

        if found_column is None:
            raise ValueError(
                f"[{self.namespace}][{key}][{json_id}] No JSON data found."
            )

        json_data = entity.get(found_column)

        if decompress:
            json_data = zlib.decompress(json_data)

        if "access_counter" in entity:
            entity["access_counter"] += int(1)
        else:
            entity["access_counter"] = int(2)

        entity["date_last"] = datetime.datetime.utcnow()

        self.client.put(entity)

        return json_data


class S3JsonDataBase(object):
    """Store NGL JSON state directly in a CloudFiles-compatible bucket.

    This is intended for private deployments where Google Datastore is not
    available. Object keys use ``<table>/<column>/<id>.json.zlib`` so existing
    tools can inspect or remove the same objects.
    """

    def __init__(self, bucket_path, table_name, columns=("v2", "v1"), client=None):
        if not bucket_path:
            raise ValueError("bucket_path is required for S3JsonDataBase")
        if not table_name:
            raise ValueError("table_name is required for S3JsonDataBase")
        if not columns:
            raise ValueError("at least one JSON column is required")

        self._client = client if client is not None else CloudFiles(bucket_path)
        self._table_name = table_name
        self._columns = tuple(columns)

    @property
    def client(self):
        return self._client

    @property
    def namespace(self):
        return self._table_name

    @property
    def kind(self):
        return "ngl_json"

    @property
    def json_columns(self):
        return self._columns

    def _key(self, json_id, column=None):
        column = column or self._columns[0]
        return "{}/{}/{}.json.zlib".format(self._table_name, column, json_id)

    @staticmethod
    def _max_json_id(keys):
        max_id = 0
        for key in keys:
            try:
                max_id = max(max_id, int(key.rsplit("/", 1)[-1].split(".", 1)[0]))
            except (TypeError, ValueError):
                continue
        return max_id

    def add_json(self, json_data, user_id, json_id=None, date=None):
        del user_id, date  # S3 objects do not need datastore entity metadata

        if json_id is not None:
            json_id = int(json_id)
            if self._client.exists(self._key(json_id)):
                raise ValueError(
                    "[{}][{}][{}] ID already exists.".format(
                        self._table_name, self.kind, json_id
                    )
                )
        else:
            prefix = "{}/{}/".format(self._table_name, self._columns[0])
            json_id = self._max_json_id(self._client.list(prefix=prefix)) + 1
            while self._client.exists(self._key(json_id)):
                json_id = uuid.uuid4().int & ((1 << 62) - 1)

        json_bytes = zlib.compress(json_data)
        if len(json_bytes) > MAX_JSON_SIZE:
            raise ValueError(
                f"JSON data too large, must be compressible to <{MAX_JSON_SIZE} bytes."
            )

        self._client.put(
            self._key(json_id),
            content=json_bytes,
            content_type="application/zlib",
            raw=True,
        )
        return json_id

    def _find_json_column(self, json_id):
        for column in self._columns:
            if self._client.exists(self._key(json_id, column)):
                return column
        return None

    def get_json(self, json_id, decompress=True):
        json_id = int(json_id)
        column = self._find_json_column(json_id)
        if column is None:
            raise ValueError(
                "[{}][{}][{}] No JSON data found.".format(
                    self._table_name, self.kind, json_id
                )
            )

        json_data = self._client.get(self._key(json_id, column), raw=True)
        if not isinstance(json_data, bytes):
            json_data = bytes(json_data)
        if decompress:
            json_data = zlib.decompress(json_data)
        return json_data
