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
    http = urllib3.PoolManager(timeout=2.0, retries=urllib3.Retry(3))

    response = {}

    for service_name, url in config['services_401'].items():
        try:
            # send an HTTP GET to the url and get the status
            r = http.request('GET', url)

            # if the HTTP status isn't 401 send an alert
            # some services require authentication so this is a valid response
            if r.status != 401:
                down_service(service_name, r.status)

            # if the service is up, change its state in the db
            # and send up alert if needed
            else:
                up_service(service_name, r.status)
        # if a connection isn't able to be made, consider the service down        
        except urllib3.exceptions.MaxRetryError:
            down_service(service_name, r.status)

    for service_name, url in config['services_403'].items():
        try:
            # send an HTTP GET to the url and get the status
            r = http.request('GET', url)

            # if the HTTP status isn't 403 send an alert
            # some services require authentication so this is a valid response
            if r.status != 403:
                down_service(service_name, r.status)

            # if the service is up, change its state in the db
            # and send up alert if needed
            else:
                up_service(service_name, r.status)
        # if a connection isn't able to be made, consider the service down        
        except urllib3.exceptions.MaxRetryError:
            down_service(service_name, r.status)

    for service_name, url in config['services'].items():
        try:
            # send an HTTP GET to the url and get the status
            r = http.request('GET', url)
            
            # if the HTTP status isn't 200 OK send an alert
            if r.status != 200:
                down_service(service_name, r.status)

            # if the service is up, change its state in the db
            # and send up alert if needed
            else:
                up_service(service_name, r.status)

        # if a connection isn't able to be made, consider the service down 
        except urllib3.exceptions.MaxRetryError:
            down_service(service_name, r.status)

        # send the response if triggered by http request        
        response = {
            "statusCode": 200,
            "body": "executed successfully"
        }
   
    return response

def up_service(service_name, status):
    body = {
        "text": "Service " + service_name + " is up with a response " + 
            "code of " + str(status) + "."
    }
    text = body.get("text")
        
    try:
        dynamo_response = table.get_item(
            Key={
                    'id': service_name
                }
        )

        item = dynamo_response['Item']
        down_state = item['down_state']
        
        # check if the service is currently tracked as down
        # send an alert that the service is now up
        if down_state == True:

            response = table.update_item(
                Key={
                    'id': service_name
                },
                UpdateExpression="set down_state = :ds",
                ExpressionAttributeValues={
                    ':ds': False
                },
                ReturnValues="UPDATED_NEW"
            )

            notify_sms(text)
            notify_slack(body)

    # catch if the db does not have any state yet and set as up
    except KeyError:
        table.put_item(
            Item={
                'id': service_name,
                'down_state': False,
            }
        )

    logger.info(text)
    
def down_service(service_name, status):
    
    body = {
        "text": "Service " + service_name + " is down with a response " +
            "code of " + str(status) + "."
    }
    text = body.get("text")

    try:
        dynamo_response = table.get_item(
            Key={
                    'id': service_name
                }
        )

        item = dynamo_response['Item']
        down_state = item['down_state']

        # check if the service is already tracked as down before alerting
        if down_state == False:
            # change the db state to down
            response = table.update_item(
                Key={
                    'id': service_name
                },
                UpdateExpression="set down_state = :ds",
                ExpressionAttributeValues={
                    ':ds': True
                },
                ReturnValues="UPDATED_NEW"
            )

            notify_sms(text)
            notify_slack(body)

    # catch if the db does not have any state yet and set as down
    except KeyError:
        # change the db state to down
        table.put_item(
            Item={
                'id': service_name,
                'down_state': True,
            }
        )

        notify_sms(text)
        notify_slack(body)

    logger.info(text)

def notify_sms(text):
    client = boto3.client('sns')
    for phone_number in config['phone_numbers']:
        client.publish(
            PhoneNumber = phone_number,
            Message = json.dumps(text)
        )

def notify_slack(body):
    http = urllib3.PoolManager()

    slack_webhook_url = config['slack_webhook_url']
    r = http.request('POST', slack_webhook_url,
                 headers={'Content-Type': 'application/json'},
                 body=json.dumps(body)
    )