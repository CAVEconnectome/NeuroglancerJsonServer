from datastoreflex import DatastoreFlex
from flask import current_app
from google.auth import credentials
from google.auth import default as default_creds

from neuroglancerjsonserver.backend import database

CACHE = {}


class DoNothingCreds(credentials.Credentials):
    def refresh(self, request):
        pass


def get_datastore_client(config):
    project_id = config.get("PROJECT_ID", None)

    if config.get("emulate", False):
        credentials = DoNothingCreds()
    elif project_id is not None:
        credentials, _ = default_creds()
    else:
        credentials, project_id = default_creds()

    client = DatastoreFlex(
        project=project_id, credentials=credentials, namespace=config.get("TABLE_NAME")
    )
    return client


def get_json_db():
    if "json_db" not in CACHE:
        client = get_datastore_client(current_app.config)
        CACHE["json_db"] = database.JsonDataBase(
            client=client, table_name=current_app.config.get("TABLE_NAME")
        )

    return CACHE["json_db"]


def get_property_db():
    if "property_db" not in CACHE:
        client = get_datastore_client(current_app.config)
        CACHE["property_db"] = database.JsonDataBase(
            client=client,
            table_name=current_app.config.get("TABLE_NAME"),
            column="segment_properties",
        )

    return CACHE["property_db"]
