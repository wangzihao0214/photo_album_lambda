import json
import boto3
import logging
import requests
from datetime import datetime
from requests_aws4auth import AWS4Auth

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

opensearch_host = 'https://vpc-photos-7kszj47gzv2gvrwrqxwyrrdelm.us-east-1.es.amazonaws.com/'


def extract_label(input):
    lexv2 = boto3.client('lexv2-runtime')
    response = lexv2.recognize_text(
        botId='4HD6KKMYIO',
        botAliasId='TSTALIASID',
        localeId='en_US',
        sessionId='test_session',
        text=input
    )
    for message in response['messages']:
        logger.info(message['content'])
    labels = []
    slots = response['sessionState']['intent']['slots']
    for slot in slots:
        if slots[slot]:
            labels.append(slots[slot]['value']['interpretedValue'])
    logger.info("Extracted labels: " + str(labels))
    return labels


def search_label(labels):
    url = opensearch_host + 'photos/_search'
    credentials = boto3.Session().get_credentials()
    aws_auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        'us-east-1',
        'es',
        session_token=credentials.token
    )
    headers = {"Content-Type": "application/json"}

    search_label = labels[0]
    for label in labels[1:]:
        search_label += (" OR " + label)
    logger.info('Searching for ' + search_label)
    data = {
        "query": {
            "match": {
                "labels": {
                    "query": search_label,
                    "fuzziness": 'AUTO'
                }
            }
        }
    }
    response = requests.post(url=url, auth=aws_auth, headers=headers, json=data)
    response = response.json()

    try:
        photos = response['hits']['hits']
    except KeyError:
        return {'results': []}

    print(photos)
    results = []
    for photo in photos:
        photo = photo['_source']
        temp_dict = {}
        temp_dict['url'] = 'https://cs6998-photos.s3.amazonaws.com/' + photo['objectKey']
        temp_dict['labels'] = photo['labels']
        results.append(temp_dict)

    # url = opensearch_host + 'photos'
    # response = requests.delete(url=url, auth=aws_auth)
    # print(response)

    return {'results': results}


def lambda_handler(event, context):
    if event['queryStringParameters']:
        labels = extract_label(event['queryStringParameters']['q'])
        results = search_label(labels)
        results = json.dumps(results)
        logger.info("Search result: " + results)
    else:
        body = "Please provide at least a label"
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,GET'
        },
        'body': results
    }

