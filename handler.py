import json
import boto3
import urllib3
import os

PHONE_NUMBERS = os.environ['PHONE_NUMBERS']

def hello(event, context):
    client = boto3.client('sns')

    http = urllib3.PoolManager(timeout=5.0)
    try:
        r = http.request('GET', 'http://www.google.com')

        if r.status != 200:
            body = {
                "message": "Google is UPPP!!11!"
            }
        else:
            body = {
                "message": "Solarwinds rewritten in 50 lines of python!11!!"
            }
            message = body.get("message")
            sms_notify(client, message)
        
        response = {
            "statusCode": 500,
            "body": json.dumps(body)
        }

        return response

    except urllib3.exceptions.MaxRetryError as e:
            body = {
                "message": "Unknown error while checking service"
            }

            response = {
                "statusCode": 500,
                "body": json.dumps(body)
            }

            return response

def sms_notify(client, message):
    for number in PHONE_NUMBERS:
        client.publish(
        PhoneNumber = number,
        Message = message
        )