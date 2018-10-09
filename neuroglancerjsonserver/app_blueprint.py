from flask import Blueprint, request, make_response, jsonify, g
from flask import current_app
import json
import time
import datetime

from neuroglancerjsonserver import database

bp = Blueprint('neuroglancerjsonserver', __name__, url_prefix="/ngl_state")
__version__ = "0.0.7"
# -------------------------------
# ------ Access control and index
# -------------------------------

@bp.route('/', methods=["GET"])
@bp.route('//', methods=["GET"])
@bp.route("/index", methods=["GET"])
def index():
    return "NeuroglancerJsonServer - version " + __version__


@bp.route
def home():
    resp = make_response()
    resp.headers['Access-Control-Allow-Origin'] = '*'
    acah = "Origin, X-Requested-With, Content-Type, Accept"
    resp.headers["Access-Control-Allow-Headers"] = acah
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    resp.headers["Connection"] = "keep-alive"
    return resp


# -------------------------------
# ------ Measurements and Logging
# -------------------------------

@bp.before_request
def before_request():
    print("NEW REQUEST:", datetime.datetime.now(), request.url)
    g.request_start_time = time.time()


@bp.after_request
def after_request(response):
    dt = (time.time() - g.request_start_time) * 1000

    url_split = request.url.split("/")
    current_app.logger.info("%s - %s - %s - %s - %f.3" %
                            (request.path.split("/")[-1], "1",
                             "".join([url_split[-2], "/", url_split[-1]]),
                             str(request.data), dt))

    print("Response time: %.3fms" % (dt))
    return response


@bp.errorhandler(500)
def internal_server_error(error):
    dt = (time.time() - g.request_start_time) * 1000

    url_split = request.url.split("/")
    current_app.logger.error("%s - %s - %s - %s - %f.3" %
                             (request.path.split("/")[-1],
                              "Server Error: " + error,
                              "".join([url_split[-2], "/", url_split[-1]]),
                              str(request.data), dt))
    return 500


@bp.errorhandler(Exception)
def unhandled_exception(e):
    dt = (time.time() - g.request_start_time) * 1000

    url_split = request.url.split("/")
    current_app.logger.error("%s - %s - %s - %s - %f.3" %
                             (request.path.split("/")[-1],
                              "Exception: " + str(e),
                              "".join([url_split[-2], "/", url_split[-1]]),
                              str(request.data), dt))
    return 500

# -------------------
# ------ Applications
# -------------------

def get_db():
    if 'db' not in g:
        g.db = database.JsonDataBase()
    return g.db

@bp.route('/<json_id>', methods=['GET'])
@bp.route('//<json_id>', methods=['GET'])
def get_json(json_id):
    db = get_db()

    json_data = db.get_json(int(json_id))

    return jsonify(json_data)


@bp.route('/', methods=['POST'])
@bp.route('//', methods=['POST'])
def add_json():
    json_data = json.loads(request.data)

    db = get_db()

    json_id = db.add_json(json_data)

    return "{}{}".format(request.url, json_id)
