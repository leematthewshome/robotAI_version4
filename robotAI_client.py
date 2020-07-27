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

#---------------------------------------------------------
# Various functions
#---------------------------------------------------------


# Function executed when queue message received
def callback(ch, method, properties, body):
    logger.debug("Callback function triggered by message")
    try:
        app_id = properties.app_id
        content = properties.content_type
        reply_to = properties.reply_to
        logger.debug("Message received from "+reply_to+" App: "+app_id+" content: "+content)
    except:
        logger.error("Not all expected properties available")

    # ensure json is readable (seems to come thru as bytes)
    #if content == "application/json":
    #    body = json.loads(body.decode("utf-8"))
    
    # Call the relevant logic to process message, based on sensor type that it relates to
    if app_id == 'environ':
        logger.debug("Loading environment variables sent from brain")
        data = json.loads(body.decode("utf-8"))
        for key in data:
            ENVIRON[key] = data[key]
    elif app_id == 'motion':
        import lib.client_motion as motion
        motion.doLogic(ENVIRON, VOICE, connection, content, reply_to, body)
    elif app_id == 'voice':
        print("About to call doLogic function...")
        VOICE.doLogic(content, body)
    else:
        logger.error("Message received from "+reply_to+" but no logic exists for "+app_id)



#---------------------------------------------------------
#Kick off sensor functions in separate processes
#---------------------------------------------------------
if __name__ == '__main__':

    # setup logging using the python logging library
    logging.basicConfig()
    logger = logging.getLogger("robotAI_client")
    logger.level = logging.DEBUG

    # Create reference to our voice class
    VOICE = client_voice.voice()

    # Setup Environment data to be shared with Sensors
    #------------------------------------------------------
    mgr = Manager()
    ENVIRON = mgr.dict()
    ENVIRON["queueSrvr"] = queueSrvr
    ENVIRON["queuePort"] = queuePort
    ENVIRON["queueUser"] = queueUser
    ENVIRON["queuePass"] = queuePass
    ENVIRON["clientName"] = clientName                              #the name assigned to our client device, eg. FrontDoor
    ENVIRON["motion"] = True                                        #flags whether to run motion sensor
    # these defaults will be updated from central on connect
    ENVIRON["SecureMode"] = False
    ENVIRON["Identify"] = False

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
        try:
            from lib import client_motionSensor
            m = Process(target=client_motionSensor.doSensor, args=(ENVIRON, ))
            m.start()
        except:
            logger.error('Failed to start motion sensor')
    

    # ---------------------------------------------------------------------------------------
    # Send connect message to Central channel and Start listening on our client channel 
    # ---------------------------------------------------------------------------------------
    if isQueue:
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
    
 
