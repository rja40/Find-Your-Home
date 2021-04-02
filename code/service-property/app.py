"""
SFU CMPT 756
Property service.
"""

# Standard library modules
import logging
import sys
import time

# Installed packages
from flask import Blueprint
from flask import Flask
from flask import request
from flask import Response

import jwt

from prometheus_flask_exporter import PrometheusMetrics

import requests

import simplejson as json

# The application

app = Flask(__name__)

metrics = PrometheusMetrics(app)
metrics.info('app_info', 'Property process')

bp = Blueprint('app', __name__)

db = {
    #"name": "http://teamadb:30000/api/v1/datastore", #For Online testing
    "name": "http://host.docker.internal:30000/api/v1/datastore", #For Local Testing
    # "name": "http://172.17.0.1:30000/api/v1/datastore", #For linux
    "endpoint": [
        "read",
        "write",
        "delete",
        "update"
    ]
}


@bp.route('/', methods=['GET'])
@metrics.do_not_track()
def hello_world():
    return ("If you are reading this in a browser, your service is "
            "operational. Switch to curl/Postman/etc to interact using the "
            "other HTTP verbs.")


@bp.route('/health')
@metrics.do_not_track()
def health():
    return Response("", status=200, mimetype="application/json")


@bp.route('/readiness')
@metrics.do_not_track()
def readiness():
    return Response("", status=200, mimetype="application/json")


@bp.route('/<user_id>', methods=['PUT'])
def update_user(user_id):
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "missing auth"}), status=401,
                        mimetype='application/json')
    try:
        content = request.get_json()
        email = content['email']
        fname = content['fname']
        lname = content['lname']
    except Exception:
        return json.dumps({"message": "error reading arguments"})
    url = db['name'] + '/' + db['endpoint'][3]
    response = requests.put(
        url,
        params={"objtype": "user", "objkey": user_id},
        json={"email": email, "fname": fname, "lname": lname})
    return (response.json())


@bp.route('/', methods=['POST'])
def create_user():
    """
    Create a user.
    If a record already exists with the same fname, lname, and email,
    the old UUID is replaced with a new one.
    """
    try:
        content = request.get_json()
        lname = content['lname']
        email = content['email']
        fname = content['fname']
    except Exception:
        return json.dumps({"message": "error reading arguments"})
    url = db['name'] + '/' + db['endpoint'][1]
    response = requests.post(
        url,
        json={"objtype": "user",
              "lname": lname,
              "email": email,
              "fname": fname})
    return (response.json())

@bp.route('/create_property', methods=['POST'])
def create_property():
    
    try:
        content = request.get_json()
        content['objtype'] = 'property'
        print(content)
        url = db['name'] + '/' + db['endpoint'][1]
        response = requests.post(
                url,
                json=content)


        print(response)
        if response.status_code == 200:

            prop_id = response.json()['property_id']
            city = content['city']
            
            url = db['name'] + '/' + db['endpoint'][1]
            response_city = requests.post(
            url,
            json={"objtype": "city",
                "city_id": city,
                "prop_id": prop_id
                })
        else:
            return Response(json.dumps({"error":"An error occurreced processing this request"}), status=401,
                                    mimetype='application/json')
        return (response.json())
        
    except Exception as e:
        return Response(json.dumps({"error":e}), status=401,
                                    mimetype='application/json')


@bp.route('/service_req', methods=['POST'])
def create_servicereq():
    """
    Create a Service Request by Tenant.
    """
    
    try:
        
        content = request.get_json()
        property_id = content['property_id']
        user_id = content['user_id']
        query = content['query']
        url = db['name'] + '/' + db['endpoint'][1]
        response = requests.post(
        url,
        json={"objtype": "service_requests",
            "property_id": property_id,
            "user_id": user_id,
            "query": query,
            "resolved": False            
            })
        
        return (response.json())

    except Exception:
        return json.dumps({"message": "error reading arguments"})
    


@bp.route('/service_req_update', methods=['PUT'])
def update_servicereq():
    """
    Update a Service Request by Tenant.
    """
    try:
        
        content = request.get_json()
        
        property_id = content['property_id']
        user_id = content['user_id']
        query = content['query']
        query_id = content['query_id']

    except Exception:
        return json.dumps({"message": "error reading arguments"})
    
    url = db['name'] + '/' + db['endpoint'][1]
    response = requests.post(
        url,
        json={"objtype": "service_requests",
            "src" : "tenant",
            "property_id": property_id,
            "user_id": user_id,
            "query_id": query_id,
            "query": query,
            "resolved": False            
            })

    return (response.json())


@bp.route('/resolve_req', methods=['PUT'])
def resolve_servicereq():
    """
    Resolve a Service Request by Landlord.
    """
   
    try:
        
        content = request.get_json()
        property_id = content['property_id']
        tenant_id = content['tenant_id']
        user_id = content['user_id']
        query_id = content['query_id']
        resolution = content['resolution']
        res = content['resolved']

    except Exception:
        return json.dumps({"message": "error reading arguments"})
    
    url = db['name'] + '/' + db['endpoint'][1]
   
    response = requests.post(
    url,
    json={"objtype": "service_requests",
        "src": 'landlord',
        "property_id": property_id,
        "tenant_id" : tenant_id,
        "user_id": user_id,
        "query_id": query_id,
        "resolution": resolution,
        "resolved": res            
        })
    
    return (response.json())
        

@bp.route('/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "missing auth"}),
                        status=401,
                        mimetype='application/json')
    url = db['name'] + '/' + db['endpoint'][2]

    response = requests.delete(url,
                               params={"objtype": "user", "objkey": user_id})
    return (response.json())


@bp.route('/<user_id>', methods=['GET'])
def get_user(user_id):
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(
            json.dumps({"error": "missing auth"}),
            status=401,
            mimetype='application/json')
    payload = {"objtype": "user", "objkey": user_id}
    url = db['name'] + '/' + db['endpoint'][0]
    response = requests.get(url, params=payload)
    return (response.json())


@bp.route('/login', methods=['PUT'])
def login():
    try:
        content = request.get_json()
        uid = content['uid']
    except Exception:
        return json.dumps({"message": "error reading parameters"})
    url = db['name'] + '/' + db['endpoint'][0]
    response = requests.get(url, params={"objtype": "user", "objkey": uid})
    data = response.json()
    if len(data['Items']) > 0:
        encoded = jwt.encode({'user_id': uid, 'time': time.time()},
                             'secret',
                             algorithm='HS256')
    return encoded


@bp.route('/logoff', methods=['PUT'])
def logoff():
    try:
        content = request.get_json()
        _ = content['jwt']
    except Exception:
        return json.dumps({"message": "error reading parameters"})
        
    return json.dumps({"message": "Successfully logged out."})


# All database calls will have this prefix.  Prometheus metric
# calls will not---they will have route '/metrics'.  This is
# the conventional organization.
app.register_blueprint(bp, url_prefix='/api/v1/property/')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error("Usage: app.py <service-port>")
        sys.exit(-1)

    p = int(sys.argv[1])
    # Do not set debug=True---that will disable the Prometheus metrics
    app.run(host='0.0.0.0', port=p, threaded=True)
