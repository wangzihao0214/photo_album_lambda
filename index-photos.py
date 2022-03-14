import json
import boto3
import logging
import requests
from datetime import datetime
from requests_aws4auth import AWS4Auth

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

opensearch_host = 'https://vpc-photos-7kszj47gzv2gvrwrqxwyrrdelm.us-east-1.es.amazonaws.com/'


def get_label(bucket, photo):
    s3 = boto3.client('s3')
    response = s3.head_object(Bucket=bucket, Key=photo)
    try:
        custom_labels = response["Metadata"]["customlabels"]
        labels = custom_labels.split(",")
    except KeyError:
        labels = []

    client = boto3.client('rekognition')
    response = client.detect_labels(
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': photo,
            }
        },
        MaxLabels=10,
        MinConfidence=90
    )

    for label in response['Labels']:
        labels.append(label['Name'])
    return labels


def post_label(photo, labels, bucket):
    data = {
        'doc': {
            'labels': labels
        },
        'upsert': {
            'objectKey': photo,
            'bucket': bucket,
            'createdTimestamp': datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
            'labels': labels
        }
    }
    data = json.dumps(data)
    url = opensearch_host + 'photos/_update/' + photo
    credentials = boto3.Session().get_credentials()
    aws_auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        'us-east-1',
        'es',
        session_token=credentials.token
    )
    headers = {"Content-Type": "application/json"}
    response = requests.post(url=url, auth=aws_auth, headers=headers, data=data)
    print(response.text)


def lambda_handler(event, context):
    logger.info("A photo has been put into S3!")
    for record in event['Records']:
        s3 = record['s3']
        bucket = s3['bucket']['name']
        photo = s3['object']['key']
        logger.info("Received photo: " + photo)
        labels = get_label(bucket, photo)
        logger.info("Attached labels: " + str(labels))
        post_label(photo, labels, bucket)

    return {
        'statusCode': 200,
        'body': json.dumps('Info uploaded to OpenSearch.')
    }
