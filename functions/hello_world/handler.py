import base64
import json

def lambda_handler(event, context):
    # TODO implement
    print("Event:", json.dumps(event))

    # if 'body' in event:
    #     decoded = base64.b64decode(event['body']).decode('utf-8')
    #     print("Body:", decoded)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
