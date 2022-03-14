import json
import datetime
import time
import os
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


# --- Helpers that build all of the responses ---


def elicit_slot(request_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        # 'requestAttributes': request_attributes,
        'sessionState': {
            'dialogAction': {
                'type': 'ElicitSlot',
                'slotToElicit': slot_to_elicit
            },
            'intent': {
                'name': intent_name,
                'slots': slots,
                'state': 'Failed'
            }
        },
        'messages': [message]
    }


def close(request_attributes, intent_name, message):
    return {
        # 'requestAttributes': request_attributes,
        'sessionState': {
            'dialogAction': {
                'type': 'Close',
            },
            'intent': {
                'name': intent_name,
                'state': 'Fulfilled'
            }
        },
        'message': [message]
    }


def delegate(request_attributes, slots):
    return {
        'requestAttributes': request_attributes,
        'sessionState': {
            'dialogAction': {
                'type': 'Delegate',
            },
            'intent': {
                'name': '',
                'slots': slots,
                'state': 'ReadyForFulfillment'
            }
        }

    }


# --- Helper Functions ---


def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n


def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except TypeError:
        return None


def build_validation_result(isvalid, violated_slot, message_content):
    return {
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def validate_search(slots):
    label1 = try_ex(lambda: slots['label1']['value']['interpretedValue'])
    label2 = try_ex(lambda: slots['label2']['value']['interpretedValue'])
    if not label1:
        return build_validation_result(
            False,
            'label1',
            'Please provide at least 1 label'
        )
    return {'isValid': True}


# --- Functions that communicate with backend ---


def push_sqs(text):
    sqs = boto3.client('sqs')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/179854536678/Q1'
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=text)


# --- Functions that control the bot's behavior ---


def photo_search(intent_request):
    """
    Performs dialog management and fulfillment for booking a hotel.

    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of requestAttributes to pass information that can be used to guide conversation
    """
    print(intent_request)
    label1 = try_ex(lambda: intent_request['sessionState']['intent']['slots']['label1']['value']['interpretedValue'])
    label2 = try_ex(lambda: intent_request['sessionState']['intent']['slots']['label2']['value']['interpretedValue'])

    request_attributes = intent_request['requestAttributes'] if 'requestAttributes' in intent_request else {}

    # Load confirmation history and track the current reservation.
    requirement = json.dumps({
        'label1': label1,
        'label2': label2,
    })

    request_attributes['currentRequirement'] = requirement

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified. If any are invalid, re-elicit for their value
        validation_result = validate_search(intent_request['sessionState']['intent']['slots'])
        if not validation_result['isValid']:
            slots = intent_request['sessionState']['intent']['slots']
            slots[validation_result['violatedSlot']] = None

            return elicit_slot(
                request_attributes,
                intent_request['sessionState']['intent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        return close(
            request_attributes,
            intent_request['sessionState']['intent']['name'],
            'Keywords extracted'
        )


# --- Intents ---


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch intentName={}'.format(intent_request['sessionState']['intent']['name']))

    intent_name = intent_request['sessionState']['intent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'SearchIntent':
        return photo_search(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


# --- Main handler ---


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
