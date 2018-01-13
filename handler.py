import json
import boto3
import urllib3
import os

def hello(event, context):
    client = boto3.client('sns')

    http = urllib3.PoolManager(timeout=5.0)
    try:
        r = http.request('GET', 'http://www.oscn.net/v4')

        if r.status == 201:
            body = {
                "message": "OSCN is UPPP!!11!"
            }
        else:
            body = {
                "message": "OSCN is dowwwwn :("
            }
            client.publish(
            PhoneNumber="+14059266362",
            Message="OSCN is dowwwwn :("
            )
        
        response = {
            "statusCode": 500,
            "body": json.dumps(body)
        }

        return response

    except urllib3.exceptions.MaxRetryError as e:
            body = {
                "message": "Service is down for unknown reason"
            }

            response = {
                "statusCode": 500,
                "body": json.dumps(body)
            }

            return response
