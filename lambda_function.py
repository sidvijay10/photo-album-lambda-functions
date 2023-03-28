import json
import boto3 

from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

from botocore.exceptions import ClientError
from datetime import datetime

s3_resource = boto3.resource('s3')
s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')

REGION = 'us-east-1'
HOST = 'search-photos-df2awflxl7ypfve2bic7gqst6y.us-east-1.es.amazonaws.com'
INDEX = 'photos'
url = "https://search-photos-df2awflxl7ypfve2bic7gqst6y.us-east-1.es.amazonaws.com/photos/_doc"

def lambda_handler(event, context):
    
    # FORMAT CUSTOM LABELS HEADER -- CONVERT TO JSON ARRAY BEFORE ADDING TO LABELS - DO WITH API
    
    metadata = s3.head_object(Bucket=event["Records"][0]["s3"]["bucket"]["name"],
                                Key=event["Records"][0]["s3"]["object"]["key"])
    print(metadata)
    created_timestamp = metadata['ResponseMetadata']['HTTPHeaders']['last-modified']
    
    response = rekognition.detect_labels(
        Image={
            'S3Object': {
                'Bucket': event["Records"][0]["s3"]["bucket"]["name"],
                'Name': event["Records"][0]["s3"]["object"]["key"],
            }
        },
    )
    
    labels = [label['Name'].lower() for label in response['Labels']]
    if 'x-amz-meta-customLabels' in metadata['ResponseMetadata']['HTTPHeaders']:
        for label in metadata['ResponseMetadata']['HTTPHeaders']['x-amz-meta-customLabels']:
            labels.append(label)

    image_data = {
        'objectKey': event["Records"][0]["s3"]["object"]["key"],
        'bucket': event["Records"][0]["s3"]["bucket"]["name"],
        'createdTimestamp': created_timestamp,
        'labels': labels,
    }

    print(image_data)
    response = upload(image_data)

    return {
        'statusCode': 200,
        'body': json.dumps(image_data)
    }

def upload(image_data):
    data = json.dumps(image_data)
    client = OpenSearch(hosts=[{
        'host': HOST,
        'port': 443
    }],
                        http_auth=get_awsauth(REGION, 'es'),
                        use_ssl=True,
                        verify_certs=True,
                        connection_class=RequestsHttpConnection)
                        
    
    res = client.index(index=INDEX, body=data)
    return res


def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    print(cred)
    return AWS4Auth(cred.access_key,
                    cred.secret_key,
                    region,
                    service,
                    session_token=cred.token)