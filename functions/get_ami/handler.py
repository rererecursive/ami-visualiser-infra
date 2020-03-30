import json
import os
import boto3

def lambda_handler(event, context):
  region  = os.environ['REGION']
  table   = os.environ['TABLE']
  items   = []

  dynamo_client = boto3.client('dynamodb', region_name=region)
  print(f"Fetching data from DynamoDB table '{table}' ...")
  response = dynamo_client.scan(TableName=table)
  print("Found %d items." % len(response['Items']))

  for item in response['Items']:
    items.append(from_dynamodb_schema(item))

  return items

def from_dynamodb_schema(input):
    output = {}

    for key, value in input.items():
      if 'S' in value:
        output[key] = value['S']

      elif 'M' in value:
        items = from_dynamodb_schema(value['M'])
        output[key] = items

    return output
