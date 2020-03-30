import sys
import os
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sys.path.append(f"{os.environ['LAMBDA_TASK_ROOT']}/lib")
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import json
import cr_response
from botocore.config import Config

client_config = Config(
    retries = dict(
        max_attempts = 10
    )
)

def lambda_handler(event, context):
    logger.info(f"Received event:{json.dumps(event)}")

    cr_params = event['ResourceProperties']
    logger.info(f"Resource Properties {json.dumps(cr_params)}")

    region = cr_params['Region']
    account_id = cr_params['AccountId']
    stack_id = cr_params['StackName']
    notification = cr_params['LambdaNotification']
    #needs the PhysicalResourceId set incase of errors during creation otherwise you'll end up with an invalid physical id
    if 'PhysicalResourceId' not in event:
        event['PhysicalResourceId'] = generate_physical_id(notification, stack_id)
    lambda_response = cr_response.CustomResourceResponse(event)

    if not notification['Bucket']:
        logger.info("Skipping notification creation as the bucket name is empty.")
        lambda_response.respond(data={}, NoEcho=False)
        return 'OK'

    try:
        if event['RequestType'] == 'Create':
            statement_id = add_lambda_notification(notification=notification, region=region, account_id=account_id, stack_id=stack_id)
            event['PhysicalResourceId'] = statement_id
            lambda_response.respond(data={'PhysicalResourceId': statement_id}, NoEcho=False)

        elif event['RequestType'] == 'Update':
            remove_lambda_notification(notification_id=event['PhysicalResourceId'], region=region)
            statement_id = add_lambda_notification(notification=notification, region=region, account_id=account_id, stack_id=stack_id)
            lambda_response.respond(data={'PhysicalResourceId': statement_id}, NoEcho=False)

        elif event['RequestType'] == 'Delete':
            remove_lambda_notification(notification_id=event['PhysicalResourceId'], region=region)
            lambda_response.respond(data={'PhysicalResourceId': event['PhysicalResourceId']}, NoEcho=False)

    except Exception as e:
        message = str(e)
        lambda_response.respond_error(message)
    return 'OK'

def generate_physical_id(notification, stack_id):
    bucket = notification['Bucket']
    function = notification['Function']
    return '%s___%s' % (bucket, function)

def add_lambda_notification(notification, region, account_id, stack_id):
    client = boto3.client('s3', region_name=region, config=client_config)

    filters = []
    bucket = notification['Bucket']
    function = notification['Function']
    # Delimited so that we can split and access the information later
    notification_id = generate_physical_id(notification, stack_id)

    # arn = 'arn:aws:lambda:%s:%s:function:%s' % (region, account_id, function)
    arn = function

    lambda_config = {
        'Id': notification_id,
        'LambdaFunctionArn': arn,
        'Events': ['s3:ObjectCreated:Put']
    }

    if 'Prefix' in notification:
        filters.append({'Name': 'prefix', 'Value': notification['Prefix']})

    if 'Suffix' in notification:
        filters.append({'Name': 'suffix', 'Value': notification['Suffix']})

    lambda_config['Filter'] = {
        'Key': {
            'FilterRules': filters
        }
    }

    logger.info("Associating Lambda function '%s' with bucket '%s' for %d paths..." % (arn, bucket, len(filters)))

    # Allow the function to be triggered from S3.
    logger.info("Adding permission to the function's policy to allow it to be triggered from S3...")
    lambda_client = boto3.client('lambda', region_name=region, config=client_config)

    try:
        lambda_client.add_permission(
            Action='lambda:InvokeFunction',
            FunctionName=function,
            Principal='s3.amazonaws.com',
            StatementId=f'ID{hash(bucket + function)}'
        )
    except lambda_client.exceptions.ResourceConflictException as e:
        logger.info(str(e))
        logger.info("Continuing execution as the policy already exists.")

    # If notifications already exist, append this new one. Don't overwrite them.
    new_config = {}
    existing_config = client.get_bucket_notification_configuration(Bucket=bucket)
    existing_config.pop('ResponseMetadata')

    if 'LambdaFunctionConfigurations' in existing_config:
        logger.info("A Lambda configuration already exists (%s); appending new notification to this list..." % existing_config['LambdaFunctionConfigurations'])
        existing_config['LambdaFunctionConfigurations'].append(lambda_config)
        new_config = existing_config
    else:
        new_config['LambdaFunctionConfigurations'] = [lambda_config]

    logger.info("Adding notification configuration to bucket '%s'..." % bucket)
    # The function has no output in the response.
    client.put_bucket_notification_configuration(
        Bucket=bucket,
        NotificationConfiguration=new_config
    )

    # We have to track the information in the below variables if future deletion is required
    return notification_id

def remove_lambda_notification(notification_id, region):
    bucket, function = notification_id.split('___')

    if not bucket:
        logger.info("Skipping notification removal as the bucket name is empty.")
        return

    logger.info("Removing permissions for the S3 event source on Lambda function '%s'..." % function)
    client = boto3.client('s3', region_name=region, config=client_config)
    lambda_client = boto3.client('lambda', region_name=region, config=client_config)

    try:
        lambda_client.remove_permission(
            FunctionName=function,
            StatementId=f'ID{hash(bucket + function)}'
        )
    except lambda_client.exceptions.ResourceNotFoundException as e:
        logger.info(str(e))
        logger.info("Continuing execution as the permissions were already deleted. OK.")

    logger.info("Removing Lambda notification from bucket '%s'..." % (bucket))
    configuration = client.get_bucket_notification_configuration(Bucket=bucket)
    configuration.pop('ResponseMetadata')

    # Keep the other the other bucket notifications if they exist
    config = configuration.get('LambdaFunctionConfigurations', '')
    if not config:
        logger.info("No Lambda function configuration exists for this bucket '%s' - it must have been deleted. OK." % notification_id)
        return

    for i, c in enumerate(config):
        if c['Id'] == notification_id:
            config.pop(i)
            configuration['LambdaFunctionConfigurations'] = config
            logger.info('Keeping existing config: %s' % configuration)
            break
    else:
        logger.info("The Lambda function configuration with Id '%s' was not found - it must have been deleted. OK." % notification_id)
        return

    # We can't delete; only 'put' with a new config.
    client.put_bucket_notification_configuration(
        Bucket=bucket,
        NotificationConfiguration=configuration
    )
