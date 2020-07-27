#!/usr/bin/python3
"""
===============================================================================================
Logic used by robotai_client to respond once an image has been processed by brain
Author: Lee Matthews 2020
===============================================================================================
"""
import logging
import json
import pika


#---------------------------------------------------------------------------
# Main function called by robotAI_client 
#---------------------------------------------------------------------------
def doLogic(ENVIRON, VOICE, QCONN, content, reply_to, body):
    debugOn = True
    
    # setup logging using the python logging library
    #-----------------------------------------------------
    logging.basicConfig()
    logger = logging.getLogger("client_motion")
    if debugOn:
        logger.level = logging.DEBUG
    else:
        logger.level = logging.INFO

     
    # load body text into dictionary
    try:
        body_json = json.loads(body.decode("utf-8"))
    except:
        logger.error("Response from brain is not a valid JSON structure")
        body_json = {}

    # Get our motion detection settings from environment
    SecureMode = ENVIRON["SecureMode"] 
    Identify = ENVIRON["Identify"] 
   
    # Check if a person was detected
    if 'person' in body_json:
        persons = body_json["person"]
    else:
        persons = 0

    # Take appropriate action based on settings
    if persons > 0:
        if SecureMode:
            body = '{"action": "getChat", "chatItem": "SECURITY-0"}'
        if Identify:
            body = '{"action": "getChat", "chatItem": "GREETA-0"}'
        # Request chat data from brain
        logger.debug("About to send this data: " +body)
        logger.debug("Sending to : " +reply_to)
        channel1 = QCONN.channel()
        channel1.queue_declare(reply_to)
        properties = pika.BasicProperties(app_id='voice', content_type='application/json', reply_to=ENVIRON["clientName"])
        channel1.basic_publish(exchange='', routing_key=reply_to, body=body, properties=properties)
        
