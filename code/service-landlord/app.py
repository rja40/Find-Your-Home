"""
SFU CMPT 756
Landlord service.
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
metrics.info('app_info', 'Landlord process')

bp = Blueprint('app', __name__)

services = {
    "property": "http://host.docker.internal:30002/api/v1/property",
    "endpoint": [
        "create_property",
        "resolve_req"
    ]
}

db = {
    # "name": "http://teamadb:30000/api/v1/datastore", #For Online testing
    "name": "http://host.docker.internal:30000/api/v1/datastore", #For Local Testing
    # "name": "http://172.17.0.1:30000/api/v1/datastore",  # For linux
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
def update_landlord(user_id):
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "missing auth"}), status=401,
                        mimetype='application/json')
    try:
        content = request.get_json()
        username = content['username']
        email = content['email']
        fname = content['fname']
        lname = content['lname']
        password = content['password']
        contact = content['contact']
    except Exception:
        return json.dumps({"message": "error reading arguments"})
    url = db['name'] + '/' + db['endpoint'][3]
    response = requests.put(
        url,
        params={"objtype": "user_details", "objkey": user_id},
        json={"username": username, "email": email, "fname": fname, "lname": lname,"password":password, "contact": contact})
    return (response.json())

@bp.route('/', methods=['POST'])
def create_landlord():
    """
    Creating a new landlord account that starts with username l_<username>. .
    """
    try:
        content = request.get_json()
        username = content['username']
        password = content['password']
        fname = content['fname']
        lname = content['lname']
        email = content['email']
        contact = content['contact']
        properties = content['properties']
    except Exception:
        return json.dumps({"message": "All landlord arguments not passed."})
    url = db['name'] + '/' + db['endpoint'][1]
    response = requests.post(
        url,
        json={"objtype": "user_details",
              "username": 'L_' + username,
              "lname": lname,
              "email": email,
              "fname": fname,
              "password": password,
              "contact": contact,
              "properties": properties})
    return (response.json())


@bp.route('/property', methods=['POST'])
def create_property():
    """
    Create a Property by Landlord. Need to update this property ID in Landlord User detail so that can be used in View Property
    """
    headers = request.headers

    # check header here
    if 'user_id' not in headers:
        return Response(json.dumps({"error": "missing auth"}), status=401,
                        mimetype='application/json')

    else:
        user_id = headers['user_id']
        if user_id.startswith('L_'):
            try:

                content = request.get_json()
                address = content['street address']
                city = content['city']
                pincode = content['pincode']
                availability = content['availability']
                beds = content['beds']
                baths = content['baths']
                rent = content['rent']
                facilities = content['facilities']



            except Exception:
                return json.dumps({"message": "error reading arguments"})

            url = services['property'] + '/' + services['endpoint'][0]

            response = requests.post(
                url,
                json={
                      "user_id": user_id,
                      "street address": address,
                      "city": city,
                      "pincode": pincode,
                      "availability": availability,
                      "beds": beds,
                      "baths": baths,
                      "rent": rent,
                      "facilities": facilities
                      })


            # '''
            # url = db['name'] + '/' + db['endpoint'][3]
            # response = requests.put(url,
            #                 params={"objtype": "user_details", "objkey": user_id, "password": password},
            #                 json={"prop": prop_id})
            # '''


            return (response.json())
        else:
            return Response(json.dumps({"error": "Only Landlord can create a property"}), status=401,
                            mimetype='application/json')

@bp.route('/resolve_req/<query_id>', methods=['PUT'])
def resolve_servicereq(query_id):
    """
    Resolve a Service Request by Landlord.
    """
    headers = request.headers
    # check header here
    if 'user_id' not in headers:

        return Response(json.dumps({"error": "missing auth"}), status=401,
                        mimetype='application/json')

    else:
        user_id = headers['user_id']
        if user_id.startswith('L_'):
            try:

                content = request.get_json()
                property_id = content['property_id']
                tenant_id = content['tenant_id']
                resolution = content['resolution']
                res = content['resolved']

            except Exception:
                return json.dumps({"message": "error reading arguments"})
            url = services['property'] + '/' + services['endpoint'][1]
            response = requests.put(
                url,
                json={
                    "property_id": property_id,
                    "tenant_id" : tenant_id,
                    "user_id": user_id,
                    "query_id": query_id,
                    "resolution": resolution,
                    "resolved": res
                    })
            return (response.json())
        else:
            return Response(json.dumps({"error": "Only Landlord can resolve a service request"}), status=401,
                        mimetype='application/json')


@bp.route('/<prop_id>', methods=['DELETE'])
def delete_property(prop_id):
    headers = request.headers

    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "Owner has not provided authorization token, user is not logged in!"}),
                        status=401,
                        mimetype='application/json')

    content = request.get_json()
    user_id = 'L_' + content['username']
    password = content['password']

    # Update user details
    url = db['name'] + '/' + db['endpoint'][3]
    response = requests.put(url,
                            params={"objtype": "user_details", "objkey": user_id, "password": password},
                            json={"prop": prop_id})

    # Delete property from property table
    if response.status_code == 200:
        url = db['name'] + '/' + db['endpoint'][2]
        response = requests.delete(url, params={"objtype": "property", "objkey": prop_id})

    else:
        return Response(json.dumps({"error1": "selected property does not belong to landlord OR",
                                    "error2": "landlord username/password is incorrect!"}), status=401,
                                    mimetype='application/json')

    return (response.json())


@bp.route('/<user_id>', methods=['GET'])
def get_landlord(user_id):
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
        username = 'L_' + content['username']
        password = content['password']
    except Exception:
        return json.dumps({"message": "error reading parameters"})
    url = db['name'] + '/' + db['endpoint'][0]
    response = requests.get(url, params={"objtype": "user_details", "objkey": username, "passkey": password})
    data = response.json()
    if data['password']==password:
        encoded = jwt.encode({'user_id': username,'time': time.time()},'secret',algorithm='HS256')
    else:
        return json.dumps({"message": "Username/Password Incorrect!!!"})
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
app.register_blueprint(bp, url_prefix='/api/v1/landlord/')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error("Usage: app.py <service-port>")
        sys.exit(-1)

    p = int(sys.argv[1])
    # Do not set debug=True---that will disable the Prometheus metrics
    app.run(host='0.0.0.0', port=p, threaded=True)
