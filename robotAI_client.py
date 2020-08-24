#!/usr/bin/python3
"""
===============================================================================================
Main code module for RobotAI Client
Runs the various sensors, and feeds input to brain. 
Author: Lee Matthews 2020
===============================================================================================
"""
#import essential python modules
import pika
import logging
import json
import os
from multiprocessing import Process, Manager, Queue

# import shared utility finctions
from lib import common_utils as utils
from lib import client_voice


#---------------------------------------------------------
# Get general configuration details and setup logging
#---------------------------------------------------------
clientName = 'ClientDefault'
queueSrvr = '192.168.0.50'
queuePort = 5672
queueUser = 'guest'
queuePass = 'guest'
debugOn = True
motionSensor = True
voiceSensor = True


#---------------------------------------------------------
# Various functions
#---------------------------------------------------------


# Function executed when queue message received
#---------------------------------------------------------
def callback(ch, method, properties, body):
    logger.debug("Callback function triggered by message")
    try:
        app_id = properties.app_id
        content = properties.content_type
        reply_to = properties.reply_to
        logger.debug("Message received from "+reply_to+" App: "+app_id+" content: "+content)
    except:
        logger.error("Not all expected properties available")

    # Call the relevant logic to process message, based on sensor type that it relates to
    if app_id == 'environ':
        # update the current environment variables 
        logger.debug("Loading environment variables sent from brain")
        data = json.loads(body.decode("utf-8"))
        for key in data:
            ENVIRON[key] = data[key]
    elif app_id == 'motion':
        # call our set of actions related to motion
        import lib.client_motion as motion
        motion.doLogic(ENVIRON, VOICE, connection, content, reply_to, body)
    elif app_id == 'voice':
        # call the set of actions related to voice
        VOICE.doLogic(content, body)
    else:
        logger.error("Message received from "+reply_to+" but no logic exists for "+app_id)



#---------------------------------------------------------
#Kick off sensor functions in separate processes
#---------------------------------------------------------
if __name__ == '__main__':

    # setup logging using the python logging library
    debugOn = False
    logging.basicConfig()
    logger = logging.getLogger("robotAI_client")
    if debugOn:
        logger.level = logging.DEBUG
    else:
        logger.level = logging.INFO

    # Setup Environment data to be shared with Sensors
    #------------------------------------------------------
    mgr = Manager()
    ENVIRON = mgr.dict()
    ENVIRON["queueSrvr"] = queueSrvr
    ENVIRON["queuePort"] = queuePort
    ENVIRON["queueUser"] = queueUser
    ENVIRON["queuePass"] = queuePass
    ENVIRON["clientName"] = clientName                                  #the name assigned to our client device, eg. FrontDoor
    ENVIRON["motion"] = motionSensor                                    #flags whether to run motion sensor
    ENVIRON["listen"] = True                                            # indicates pyaudio is free for hotword detection
    ENVIRON["topdir"] = os.path.dirname(os.path.realpath(__file__))
    # these defaults will be updated from central on connect
    ENVIRON["secureMode"] = False
    ENVIRON["friendMode"] = True
    ENVIRON["talking"] = False			 

    # Create reference to our voice class
    VOICE = client_voice.voice(ENVIRON)

    # define some variables
    isWWWeb = False
    isQueue = False

    # test internet connection
    isWWWeb = utils.testInternet(logger, 5, "www.google.com")

    # Try and connect to the message queue
    #------------------------------------------------------
    try:
        credentials = pika.PlainCredentials(queueUser, queuePass)
        parameters = pika.ConnectionParameters(queueSrvr, queuePort, '/',  credentials)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue='Central')
        isQueue = True
        logger.debug('Connected to Message Queue ' + queueSrvr)
    except:
        logger.error('Unable to connect to Message Queue ' + queueSrvr)

    
    # ---------------------------------------------------------------------------------------
    # kick off motion sensor process based on enabled = TRUE
    # ---------------------------------------------------------------------------------------
    if motionSensor:
        logger.info("Starting motion sensor")
        try:
            from lib import client_motionSensor
            m = Process(target=client_motionSensor.doSensor, args=(ENVIRON, ))
            m.start()
        except:
            logger.error('Failed to start motion sensor')
    


    # ---------------------------------------------------------------------------------------
    # kick off voice sensor process based on enabled = TRUE
    # ---------------------------------------------------------------------------------------
    if voiceSensor:
        logger.info("Starting voice sensor")
        try:
            from lib import client_voiceSensor
            m = Process(target=client_voiceSensor.doSensor, args=(ENVIRON, VOICE,))
            m.start()
        except:
            logger.error('Failed to start voice sensor')
    
    
    
    # ---------------------------------------------------------------------------------------
    # Send connect message to Central channel and Start listening on our client channel 
    # ---------------------------------------------------------------------------------------
    if isQueue:
        logger.info("Sending connection message to message queue")
        properties = pika.BasicProperties(app_id='connect', content_type='text', reply_to=clientName)
        body = clientName 
        channel.basic_publish(exchange='', routing_key='Central', body=body, properties=properties)
        channel.queue_declare(queue=clientName)

        try:
            logger.debug('Starting to listen on channel ' + clientName)
            channel.basic_consume(queue=clientName, on_message_callback=callback, auto_ack=True)
            channel.start_consuming()
        except:
            logger.error('Failed to start listening on channel ' + clientName)

 
