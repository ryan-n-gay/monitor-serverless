import os
import json
import yaml
import boto3
import urllib3

with open('./config.yml') as fp:
    config = yaml.load(fp)

def entry(event, context):
    client = boto3.client('sns')
    http = urllib3.PoolManager(timeout=5.0)
    response = {}
    try:
        for service_name, url in config['services'].items():
            r = http.request('GET', url)

            if r.status == 200:
                body = {
                    "message": "Service " + service_name + " is down."
                }
                message = body.get("message")
                sms_notify(client, message)
        response = {
        "statusCode": 200,
        "body": "executed successfully"
        }
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
    for phone_number in config['phoneNumbers']:
        client.publish(
            PhoneNumber = phone_number,
            Message = message
            )