#!/usr/bin/python3
"""
===============================================================================================
Main code module for RobotAI Central Brain
Does the heavy thinking on behalf of the RobotAI clients. 
Author: Lee Matthews 2020
===============================================================================================
"""
# import essential python modules
import pika
import socket
import logging
import os

# import shared utility finctions
from lib import common_utils as utils


#---------------------------------------------------------
# Will eventually work out a place to store config data
# Just hard code in here for now
#---------------------------------------------------------
clientName = 'Central'
queueSrvr = '192.168.0.50'
queuePort = 5672
queueUser = 'guest'
queuePass = 'guest'
debugOn = True


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
    
    # Call the relevant logic to process message, based on sensor type that it relates to
    if app_id == 'connect':
        import json
        body = json.dumps(ENVIRON)        
        channel1 = connection.channel()
        channel1.queue_declare(reply_to)
        properties = pika.BasicProperties(app_id='environ', content_type='application/json', reply_to=clientName)
        channel1.basic_publish(exchange='', routing_key=reply_to, body=body, properties=properties)
    elif app_id == 'motion':
        import lib.brain_motion as motion
        motion.doLogic(ENVIRON, connection, content, reply_to, body)
    elif app_id == 'voice':
        import lib.brain_voice as voice
        voice.doLogic(ENVIRON, connection, content, reply_to, body)
    else:
        logger.error("Message received from "+reply_to+" but no logic exists for "+app_id)
    


#---------------------------------------------------------
#Kick off sensor functions in separate processes
#---------------------------------------------------------
if __name__ == '__main__':

    # setup logging using the python logging library
    #-----------------------------------------------------
    logging.basicConfig()
    logger = logging.getLogger("robotAI_brain")
    if debugOn:
        logger.level = logging.DEBUG
    else:
        logger.level = logging.INFO

    # Setup Environment data to be shared with clients
    #-----------------------------------------------------
    ENVIRON = {}
    ENVIRON["topdir"] = os.path.dirname(os.path.realpath(__file__))
    ENVIRON["SecureMode"] = False
    ENVIRON["Identify"] = True

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


    # If successful start listening on Central channel 
    #------------------------------------------------------
    if isQueue:
        try:
            logger.debug('Starting to listen on channel ' + clientName)
            channel.basic_consume(queue=clientName, on_message_callback=callback, auto_ack=True)
            channel.start_consuming()
            logger.debug('Now listening on channel ' + clientName)
        except:
            logger.error('Failed to start listening on channel ' + clientName)
    
   
