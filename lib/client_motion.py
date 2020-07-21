#!/usr/bin/python3
"""
===============================================================================================
Logic used by robotai_client to respond once an image has been processed by brain
Author: Lee Matthews 2020
===============================================================================================
"""
import logging
import json


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
        body_json = json.loads(body)
    else:
        logger.error("Response from brain is not a valid JSON structure")
        body_json = {}

    # Get our motion detection settings from environment
    SecureMode = ENVIRON["SecureMode"] 
    Identify = ENVIRON["Identify"] 
   
    # Check if a person was detected
    if 'person' in body_json:
        persons = body_json["person"]
        
    # If a person was detected then we take relevant action
    if persons > 0:
        if SecureMode:
            VOICE.say("Who are you and why are you here?")
        if Identify:
            VOICE.say("Hello there.")
        