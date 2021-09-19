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
def doLogic(ENVIRON, VOICE, QCONN, logger, content, reply_to, body):
    debugOn = True
    
    # load body text into dictionary
    logger.debug("Converting body to utf-8 text and json object")
    try:
        body_json = json.loads(body.decode("utf-8"))
    except:
        logger.error("Response from brain is not a valid JSON structure")
        body_json = {}
    
    # Check if JSON is regarding a person being detected
    if 'person' in body_json:
        persons = body_json["person"]
    else:
        persons = 0
    logger.debug("Persons detected = " + str(persons))

    # Check if JSON is regarding a face being identified
    if 'faces' in body_json:
        facelist = body_json["faces"]
        faces = len(facelist)
    else:
        faces = 0
    logger.debug("Faces detected = " + str(faces))
    
    # If we recognised face(s) then set interrupt & start new chat
    #-------------------------------------------------------------
    if faces > 0:
        logger.debug(str(facelist))
        # if we have not already recognised someone, then check list of faces
        recognized = ENVIRON["recognized"]
        if recognized:
            logger.debug("Already have recognized someone. Skipping till ENVIRON cleared")
        else:
            logger.debug("Faces recognized. Setting to interrupt speech")
            sep = ""
            faceStr = ""
            for id in facelist:
                # ignore unknown faces
                if id != 'unknown':
                    faceStr = faceStr + sep + id  
                    sep = ", "
            #only interrupt if we detected a named face. Forget them after 60 seconds
            if len(faceStr) > 0:
                ######################################################################################
                # TODO need to interrupt chat but cannot while MsgQ reader waits for responses to finish 
                ######################################################################################
                # Reset delay for when next action taken in client_motionSensor 
                ENVIRON["motionTime"] = datetime.datetime.now() + datetime.timedelta(seconds=ENVIRON["motionDelay"])
                # Trigger chat with recognised person via message queue                
                ENVIRON["recognized"] = faceStr
                ENVIRON["recognizeClear"] = datetime.datetime.now() + datetime.timedelta(seconds=60)
                body = '{"action": "getChat", "chatItem": "RECOG-0"}'
                logger.debug("About to send this data: " +body+"  to "+reply_to)
                sendToMQ(ENVIRON, QCONN, reply_to, body)
                return

    # Take action if person was detected 
    # But to prevent double conversations: only if delay expired...and if we have not recognised someone
	#-------------------------------------------------------------
    if persons > 0 and ENVIRON["motionTime"] < datetime.datetime.now():
    
        # Reset delay for when next action taken in client_motionSensor 
        ENVIRON["motionTime"] = datetime.datetime.now() + datetime.timedelta(seconds=ENVIRON["motionDelay"])
        
        if ENVIRON["talking"]:
            logger.debug("We are already talking on this device, so ignoring motion for now")
        else:
            # trigger recording of video if we are in secureMode 
            if ENVIRON["secureMode"] =="True":
                #body = '{"action": "getChat", "chatItem": "SECURITY-0"}'
                if ENVIRON["saveVideo"] is None:
                    ENVIRON["saveVideo"] = datetime.datetime.now() + datetime.timedelta(seconds=ENVIRON["videoTime"])
                    
            # trigger chat path if we are in friendMode 
            if ENVIRON["friendMode"]=="True":
                body = '{"action": "getChat", "chatItem": "GREET1-0"}'
                logger.debug("About to send this data: " +body+"  to "+reply_to)
                sendToMQ(ENVIRON, QCONN, reply_to, body)
    else:
         logger.debug("0 person detected in image so not starting chat/warning")


#---------------------------------------------------------------------------
# Function to send chat trigger 
#---------------------------------------------------------------------------
def sendToMQ(ENVIRON, QCONN, reply_to, body):
    # Request chat data from brain
    channel1 = QCONN.channel()
    channel1.queue_declare(reply_to)
    properties = pika.BasicProperties(app_id='voice', content_type='application/json', reply_to=ENVIRON["clientName"])
    channel1.basic_publish(exchange='', routing_key=reply_to, body=body, properties=properties)
