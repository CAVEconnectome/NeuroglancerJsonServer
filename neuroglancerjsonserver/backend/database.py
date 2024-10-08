import datetime
import os
import zlib

from datastoreflex import DatastoreFlex
from google.cloud import datastore

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
