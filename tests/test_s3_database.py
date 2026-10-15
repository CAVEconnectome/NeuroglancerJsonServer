import zlib

import pytest

from neuroglancerjsonserver.app.app_utils import CACHE, get_json_db
from neuroglancerjsonserver.backend.database import S3JsonDataBase


class FakeCloudFiles:
    def __init__(self):
        self.objects = {}

    def exists(self, path):
        return path in self.objects

    def get(self, path, raw=False):
        if path not in self.objects:
            raise KeyError(path)
        return self.objects[path] if raw else zlib.decompress(self.objects[path])

    def put(self, path, content, content_type=None, raw=False):
        del content_type
        if not raw:
            raise AssertionError("S3 state objects must be written raw")
        self.objects[path] = content

    def list(self, prefix=""):
        return (key for key in self.objects if key.startswith(prefix))


def test_s3_database_roundtrip_uses_existing_object_layout():
    client = FakeCloudFiles()
    db = S3JsonDataBase(
        bucket_path="s3://example/json-state",
        table_name="ngl_state",
        columns=("v2", "v1"),
        client=client,
    )

    state = b'{"layers": []}'
    state_id = db.add_json(state, user_id="1", json_id=123)

    assert state_id == 123
    assert client.objects["ngl_state/v2/123.json.zlib"] == zlib.compress(state)
    assert db.get_json(123) == state


def test_s3_database_refuses_duplicate_id():
    db = S3JsonDataBase(
        bucket_path="s3://example/json-state",
        table_name="ngl_state",
        client=FakeCloudFiles(),
    )
    db.add_json(b"{}", user_id="1", json_id=2)

    with pytest.raises(ValueError, match="ID already exists"):
        db.add_json(b"{}", user_id="1", json_id=2)


def test_s3_database_reads_legacy_v1_column():
    client = FakeCloudFiles()
    client.objects["ngl_state/v1/7.json.zlib"] = zlib.compress(b'{"v": 1}')
    db = S3JsonDataBase(
        bucket_path="s3://example/json-state",
        table_name="ngl_state",
        client=client,
    )

    assert db.get_json(7) == b'{"v": 1}'


def test_app_uses_s3_backend_when_bucket_path_is_configured():
    CACHE.clear()
    app = type("App", (), {"config": {"NGLSTATE_BUCKET_PATH": "s3://example/json-state", "TABLE_NAME": "ngl_state"}})()

    with pytest.MonkeyPatch.context() as patch_context:
        patch_context.setattr("neuroglancerjsonserver.app.app_utils.current_app", app, raising=False)
        db = get_json_db()

    assert isinstance(db, S3JsonDataBase)
    CACHE.clear()
