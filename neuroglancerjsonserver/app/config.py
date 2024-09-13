import logging
import os


class BaseConfig(object):
    DEBUG = False
    TESTING = False
    HOME = os.path.expanduser("~")
    CORS_HEADERS = "Content-Type"
    SECRET_KEY = "1d94e52c-1c89-4515-b87a-f48cf3cb7f0b"

    LOGGING_FORMAT = '{"source":"%(name)s","time":"%(asctime)s","severity":"%(levelname)s","message":"%(message)s"}'
    LOGGING_DATEFORMAT = "%Y-%m-%dT%H:%M:%S.0Z"
    LOGGING_LEVEL = logging.DEBUG
    JSON_SORT_KEYS = False

    TABLE_NAME = os.environ.get("JSON_DB_TABLE_NAME")

    PROJECT_ID = os.environ.get("PROJECT_ID")
