import os

from datastoreflex import DatastoreFlex

JSON_DB_TABLE_NAME = os.environ.get("JSON_DB_TABLE_NAME")
PROJECT_ID = os.environ.get("PROJECT_ID")
NGLSTATE_BUCKET_PATH = os.environ.get("NGLSTATE_BUCKET_PATH")
NGLSTATE_BUCKET_COLUMN = os.environ.get("NGLSTATE_BUCKET_COLUMN", "v2")
client = DatastoreFlex(project=PROJECT_ID, namespace=JSON_DB_TABLE_NAME)
config = {
    NGLSTATE_BUCKET_COLUMN: {"bucket_path": NGLSTATE_BUCKET_PATH, "path_elements": []}
}
client.add_config(config)
