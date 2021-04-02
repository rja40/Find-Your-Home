"""
SFU CMPT 756
Sample application---database service.
"""

# Standard library modules
import base64
import logging
import os
import sys
import urllib.parse
import uuid

# Installed packages

import boto3
from boto3.dynamodb.conditions import Key

from flask import Blueprint
from flask import Flask
from flask import request
from flask import Response

from prometheus_flask_exporter import PrometheusMetrics

import simplejson as json

# The application

app = Flask(__name__)

metrics = PrometheusMetrics(app)
metrics.info('app_info', 'Database process')

bp = Blueprint('app', __name__)

# default to us-east-1 if no region is specified
# (us-east-1 is the default/only supported region for a starter account)
region = os.getenv('AWS_REGION', 'us-east-1')

# these must be present; if they are missing, we should probably bail now
access_key = os.getenv('AWS_ACCESS_KEY_ID')
secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

# this is only needed for starter accounts
session_token = os.getenv('AWS_SESSION_TOKEN')

# Must be presented to authorize call to `/load`
loader_token = os.getenv('SVC_LOADER_TOKEN')

# if session_token is not present in the environment, assume it is a
# standard acct which doesn't need one; otherwise, add it on.
if not session_token:
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_access_key)
else:
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token)


# Upsert service request function
def upsert_service_req(table_name, content, query_id=None):
    table = dynamodb.Table(table_name)
    table_id = 'property_id'

    if query_id is None:
        query_id = 'Q_' + str(uuid.uuid4())

    try:
        # check if user_id already raised a service request, then upsert service request

        result = table.update_item(
            Key={
                table_id: content['property_id']
            },
            UpdateExpression="SET service_request.#user_id.#query_id = :query_id",
            ExpressionAttributeNames={
                "#user_id": content['user_id'],
                "#query_id": query_id
            },
            ExpressionAttributeValues={
                ":query_id": {
                    "query_str": content['query'],
                    "resolved": content['resolved']
                }
            },
            ConditionExpression="attribute_exists(service_request.#user_id)",
            ReturnValues="UPDATED_NEW"

        )
    except:
        try:

            # if user never raised a service request
            result = table.update_item(
                Key={
                    table_id: content['property_id']
                },
                UpdateExpression="SET service_request.#user_id = :user_id",
                ExpressionAttributeNames={
                    "#user_id": content['user_id']
                },
                ExpressionAttributeValues={
                    ":user_id": {
                        query_id: {
                            "query_str": content['query'],
                            "resolved": content['resolved']
                        }
                    }
                },
                ConditionExpression="attribute_not_exists(service_request.#user_id)",
                ReturnValues="UPDATED_NEW"

            )
        except:
            try:

                # if service request was never raised for the property
                payload = {
                    table_id: content['property_id'],
                    'service_request': {
                        content['user_id']: {
                            query_id: {
                                "query_str": content['query'],
                                "resolved": content['resolved']
                            }
                        }
                    }
                }

                result = table.put_item(Item=payload)
                result['query_id'] = query_id

            except Exception as E:
                pass
    return result


def resolve_service_req(table_name, content):
    table = dynamodb.Table(table_name)
    table_id = 'property_id'

    try:
        # Resolve a service request. Since we are not passing the query, so it will be lost and hence we are passing resolution

        result = table.update_item(
            Key={
                table_id: content['property_id']
            },
            UpdateExpression="SET service_request.#tenant_id.#query_id = :query_id",
            ExpressionAttributeNames={
                "#tenant_id": content['tenant_id'],
                "#query_id": content['query_id'],
            },
            ExpressionAttributeValues={
                ":query_id": {
                    "resolution": content['resolution'],
                    "resolved": content['resolved']
                }
            },

            ConditionExpression="attribute_exists(service_request.#tenant_id.#query_id)"
        )
    except Exception as e:
        print(e)
        # pass

    return result


def get_property_list(table_name, table_id, obj_key, passkey):
    """this function is used to return the list of properties for the particular user."""
    table = dynamodb.Table(table_name)
    try:
        resp = table.get_item(Key={table_id: obj_key})
        property_list = resp['Item']['properties']

    except:
        print("user credentials do not match")

    return table, property_list


# Change the implementation of this: you should probably have a separate
# driver class for interfacing with a db like dynamodb in a different file.
@bp.route('/update', methods=['PUT'])
def update():
    headers = request.headers
    # check header here
    content = request.get_json()

    objtype = urllib.parse.unquote_plus(request.args.get('objtype'))
    objkey = urllib.parse.unquote_plus(request.args.get('objkey'))
    table_name = objtype + "-ZZ-REG-ID"
    table_id = objtype + "_id"

    if objtype == 'user_details':
        table_id = "user_id"
        # password = urllib.parse.unquote_plus(request.args.get('password'))

        if content.get('prop',0) != 0:
            prop_id = content['prop']
            try:
                table, property_list = get_property_list(table_name, table_id, objkey)
                prop_index = property_list.index(prop_id)

                response = table.update_item(Key={table_id: objkey},
                                             UpdateExpression=f'REMOVE properties[{prop_index}]')
            except:
                return Response(
                    json.dumps({"message": "Property does not exist for user"}),
                    status=401,
                    mimetype='application/json')

            return response

        else:
            table = dynamodb.Table(table_name)
            expression = 'SET '
            x = 1
            attrvals = {}
            for k in content.keys():
                print(content.keys())
                expression += k + ' = :val' + str(x) + ', '
                attrvals[':val' + str(x)] = content[k]
                x += 1
            expression = expression[:-2]
            response = table.update_item(Key={table_id: objkey},
                                         UpdateExpression=expression,
                                         ExpressionAttributeValues=attrvals)
            return response



    table = dynamodb.Table(table_name)
    expression = 'SET '
    x = 1
    attrvals = {}
    for k in content.keys():
        expression += k + ' = :val' + str(x) + ', '
        attrvals[':val' + str(x)] = content[k]
        x += 1
    expression = expression[:-2]
    response = table.update_item(Key={table_id: objkey},
                                 UpdateExpression=expression,
                                 ExpressionAttributeValues=attrvals)
    return response


def get_password(table_name, table_id, obj_key):
    """this function is used will return the password for the given username."""
    table = dynamodb.Table(table_name)
    try:
        resp = table.get_item(Key={table_id: obj_key})
        password = resp['Item']['password']

    except:
        print("user credentials do not match")

    return password


@bp.route('/read', methods=['GET'])
def read():
    headers = request.headers
    # check header here
    objtype = urllib.parse.unquote_plus(request.args.get('objtype'))
    objkey = urllib.parse.unquote_plus(request.args.get('objkey'))
    table_name = objtype + "-ZZ-REG-ID"
    table_id = objtype + "_id"

    if objtype == 'user_details':
        table_id = "user_id"
        passkey = urllib.parse.unquote_plus(request.args.get('passkey'))

        table = dynamodb.Table(table_name)
        fetch_password =  get_password(table_name, table_id,objkey)
        if fetch_password==passkey:
            return json.dumps({'password': fetch_password})
        else:
            return json.dumps({'password': "Login Unsuccessfull"})


    table = dynamodb.Table(table_name)
    response = table.query(Select='ALL_ATTRIBUTES',
                           KeyConditionExpression=Key(table_id).eq(objkey))

    return response


@bp.route('/write', methods=['POST'])
def write():
    headers = request.headers
    # check header here
    content = request.get_json()
    table_name = content['objtype'] + "-ZZ-REG-ID"
    objtype = content['objtype']
    table_id = objtype + "_id"

    if objtype == 'property':
        payload = {table_id: 'P_' + str(uuid.uuid4())}  # Property ID
        del content['objtype']
        for k in content.keys():
            payload[k] = content[k]
        table = dynamodb.Table(table_name)
        response = table.put_item(Item=payload)
        returnval = ''
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            returnval = {"message": "fail"}
        return json.dumps(
            ({table_id: payload[table_id]}, returnval)['returnval' in globals()])


    # Update a Service Request by Tenant
    elif objtype == 'service_requests' and 'query_id' in content.keys() and content['src'] == 'tenant':
        response = upsert_service_req(table_name, content, content['query_id'])
        returnval = ''
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            returnval = {"message": "fail"}
        value = response['Attributes']['service_request'][content['user_id']].items()
        for i, j in value:
            ans = i

        return json.dumps(
            ({'query_id': ans}, returnval)['returnval' in globals()])


    elif objtype == 'service_requests' and 'query_id' in content.keys() and content['src'] == 'landlord':
        response = resolve_service_req(table_name, content)
        returnval = ''
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            returnval = {"message": "fail"}
        return json.dumps(
            ({table_id: content['property_id']}, returnval)['returnval' in globals()])

    # Create a Service Request
    elif objtype == 'service_requests':

        response = upsert_service_req(table_name, content)
        returnval = ''
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            returnval = {"message": "fail"}
        if 'query_id' not in response.keys():
            value = response['Attributes']['service_request'][content['user_id']].items()
            for i, j in value:
                ans = i

            return json.dumps(
                ({'query_id': ans}, returnval)['returnval' in globals()])

        else:
            return json.dumps(
                ({'query_id': response['query_id']}, returnval)['returnval' in globals()])

    elif objtype == 'user_details':
        table_id = "user_id"
        payload = {table_id: content['username']}

    elif objtype == 'city':
        payload = {table_id: content['city_id']}  # City name is the Key Here
        del content['objtype']
        table = dynamodb.Table(table_name)
        try:
            resp = table.get_item(Key={table_id: content['city_id']})

            #payload['properties'] = content['prop_id']
            if ('Item' in resp.keys()):
                print("EXISTING PROPERTY")
                properties = resp['Item']['properties']
                properties.append(content['prop_id'])
                payload['properties'] = properties
                response = table.put_item(Item=payload)
                returnval = ''
                if response['ResponseMetadata']['HTTPStatusCode'] != 200:
                    returnval = {"message": "fail"}
                return json.dumps(
                    ({table_id: payload[table_id]}, returnval)['returnval' in globals()])


            else:
                print("NEW PROPERTY")
                payload['properties'] = [(content['prop_id'])]
                response = table.put_item(Item=payload)
                returnval = ''
                if response['ResponseMetadata']['HTTPStatusCode'] != 200:
                    returnval = {"message": "fail"}
                return json.dumps(
                    ({table_id: payload[table_id]}, returnval)['returnval' in globals()])

        except:
            pass


    else:
        payload = {table_id: str(uuid.uuid4())}

    del content['objtype']
    for k in content.keys():
        payload[k] = content[k]
    table = dynamodb.Table(table_name)
    response = table.put_item(Item=payload)
    returnval = ''
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        returnval = {"message": "fail"}
    return json.dumps(
        ({table_id: payload[table_id]}, returnval)['returnval' in globals()])


def decode_auth_token(token):
    """Given an auth token in Base64 encoding, return the original string"""
    return base64.standard_b64decode(token).decode()


def load_auth(headers):
    """Return True if caller authorized to do a `/load` """
    global loader_token
    if 'Authorization' not in headers:
        return False
    # Auth string is 'Basic ' concatenated with base64 encoding of uname:passwd
    auth_string = headers['Authorization'].split()[1]
    name, pwd = decode_auth_token(auth_string).split(':')
    if name != 'svc-loader' or pwd != loader_token:
        return False
    return True


@bp.route('/load', methods=['POST'])
def load():
    """
    Load a value into the database

    This differs from write() in the following ways:
    1. The caller must specify the UUID in `content`. http_status_code
       400 is returned if this condition is not met.
    2. The caller must include an "Authorization" header accepted
       by load_auth(). A 401 status is returned for authorization failure.
    3. If the database returns a non-200 status code, this routine
       responds with an {http_status_code: status} object.

    This routine potentially could share a common subroutine with
    write() but the HTTP error processing in write() seems wrong
    so this routine has its own code.
    """
    headers = request.headers
    if not load_auth(headers):
        return Response(
            json.dumps({"http_status_code": 401,
                        "reason": "Invalid authorization for /load"}),
            status=401,
            mimetype='application/json')

    content = request.get_json()
    if 'uuid' not in content:
        return json.dumps({"http_status_code": 400, "reason": 'Missing uuid'})
    table_name = content['objtype'].capitalize() + "-ZZ-REG-ID"
    objtype = content['objtype']
    table_id = objtype + "_id"
    payload = {table_id: content['uuid']}
    del content['objtype']
    del content['uuid']
    for k in content.keys():
        payload[k] = content[k]
    table = dynamodb.Table(table_name)
    response = table.put_item(Item=payload)
    status = response['ResponseMetadata']['HTTPStatusCode']
    if status != 200:
        return json.dumps({"http_status_code": status})
    return json.dumps({table_id: payload[table_id]})


@bp.route('/delete', methods=['DELETE'])
def delete():
    headers = request.headers
    # check header here
    objtype = urllib.parse.unquote_plus(request.args.get('objtype'))
    objkey = urllib.parse.unquote_plus(request.args.get('objkey'))
    table_name = objtype + "-ZZ-REG-ID"
    table_id = objtype + "_id"
    table = dynamodb.Table(table_name)
    response = table.delete_item(Key={table_id: objkey})
    return response


@bp.route('/health')
@metrics.do_not_track()
def health():
    return Response("", status=200, mimetype="application/json")


@bp.route('/readiness')
@metrics.do_not_track()
def readiness():
    return Response("", status=200, mimetype="application/json")


# All database calls will have this prefix.  Prometheus metric
# calls will not---they will have route '/metrics'.  This is
# the conventional organization.
app.register_blueprint(bp, url_prefix='/api/v1/datastore/')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error("missing port arg 1")
        sys.exit(-1)

    p = int(sys.argv[1])
    # Do not set debug=True---that will disable the Prometheus metrics
    app.run(host='0.0.0.0', port=p, threaded=True)
