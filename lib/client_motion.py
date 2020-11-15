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
import datetime

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
    logger.debug("Converting body to utf-8 text and json object")
    try:
        body_json = json.loads(body.decode("utf-8"))
    except:
        logger.error("Response from brain is not a valid JSON structure")
        body_json = {}
    
    # Check if a person was detected
    if 'person' in body_json:
        persons = body_json["person"]
    else:
        persons = 0
    logger.debug("Persons detected = " + str(persons))

    # Take appropriate action based on settings
    if persons > 0:
        # Reset delay for when next action taken in client_motionSensor 
        ENVIRON["motionTime"] = datetime.datetime.now() + datetime.timedelta(seconds=ENVIRON["motionDelay"])
        
        if ENVIRON["talking"]:
            logger.debug("We are already talking on this device, so ignoring motion for now")
        else:
            print(ENVIRON)
            if ENVIRON["secureMode"] =="True":
                body = '{"action": "getChat", "chatItem": "SECURITY-0"}'
            elif ENVIRON["friendMode"]=="True":
                body = '{"action": "getChat", "chatItem": "GREETA-0"}'
            # Request chat data from brain
            logger.debug("About to send this data: " +body)
            logger.debug("Sending to : " +reply_to)
            channel1 = QCONN.channel()
            channel1.queue_declare(reply_to)
            properties = pika.BasicProperties(app_id='voice', content_type='application/json', reply_to=ENVIRON["clientName"])
            channel1.basic_publish(exchange='', routing_key=reply_to, body=body, properties=properties)
    else:
         logger.debug("0 person detected in image, so taking no action")


