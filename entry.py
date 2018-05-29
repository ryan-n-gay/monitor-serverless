import os
import json
import yaml
import boto3
import urllib3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['DYNAMODB_TABLE']
table = dynamodb.Table(table_name)

logger.info("DynamoDB Table Name: " + table_name)

with open('./config.yml') as fp:
    config = yaml.load(fp)

def entry(event, context):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    http = urllib3.PoolManager(timeout=5.0)

    response = {}
    try:
        for service_name, url in config['services'].items():
            # send an HTTP GET to the url and get the status
            r = http.request('GET', url)
            
            # if the HTTP status for OCIS isn't 401 send an alert
            # OCIS requires authentication so this is a valid response
            if service_name == 'OCIS' and r.status != 401:
                dynamo_response = table.get_item(
                    Key={
                            'id': service_name
                        }
                )

                item = dynamo_response['Item']
                tracked_state = item['down_state']

                if tracked_state != '1':
                    down_service(service_name, r.status)

            # for all other services, if the HTTP status isn't 200 OK send an alert
            elif service_name != 'OCIS' and r.status != 200:
                dynamo_response = table.get_item(
                    Key={
                            'id': service_name
                        }
                )

                item = dynamo_response['Item']
                tracked_state = item['down_state']

                if tracked_state != '1':
                    down_service(service_name, r.status)

            else:
                table.put_item(
                    Item={
                        'id': service_name,
                        'down_state': 0,
                    }
                )

                logger.info("Service " + service_name + " is up")

        # send the response if triggered by http request        
        response = {
        "statusCode": 200,
        "body": "executed successfully"
        }
   
    except urllib3.exceptions.MaxRetryError:
        body = {
            "message": "Unknown error while checking service"
        }

        response = {
            "statusCode": 500,
            "body": json.dumps(body)
        }
        logger.error("Unknown error while checking service")

    return response

def down_service(service_name, status):
    body = {
        "message": "Service " + service_name + " is down with a response " +
                    "code of " + str(status) + "."
    }
    message = body.get("message")

    table.put_item(
            Item={
                'id': service_name,
                'down_state': 1,
            }
    )

    notify_sms(message)
    notify_slack(body)

    logger.warn(message)

def notify_sms(message):
    client = boto3.client('sns')
    for phone_number in config['phone_numbers']:
        client.publish(
            PhoneNumber = phone_number,
            Message = message
        )

def notify_slack(message):
    http = urllib3.PoolManager()

    slack_webhook_url = config['slack_webhook_url']
    r = http.request('POST', slack_webhook_url,
                 headers={'Content-Type': 'application/json'},
                 body=json.dumps(message)
    )