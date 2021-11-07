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
import configparser
import base64
from multiprocessing import Process


# import shared utility functions (this also sets some common variables)
from lib import common_utils as utils


#---------------------------------------------------------
# Fetch our config variables from config file
#---------------------------------------------------------
topdir = os.path.dirname(os.path.realpath(__file__))
myfile = os.path.join(topdir, 'settings.ini')
config = configparser.ConfigParser()
config.read(myfile)


#---------------------------------------------------------
# Various functions
#---------------------------------------------------------

# Function executed when queue message received
# -------------------------------------------------------
def callback(ch, method, properties, body):
    try:
        app_id = properties.app_id
        content = properties.content_type
        reply_to = properties.reply_to
        logger.debug("Message received from "+reply_to+" App: "+app_id+" content: "+content)
    except:
        logger.error("Not all expected properties available")
    
    # Call the relevant logic to process message, based on sensor type that it relates to
    if app_id == 'connect':
        # For connection events send the current environment data to client
        import json
        body = json.dumps(ENVIRON)        
        channel1 = connection.channel()
        channel1.queue_declare(reply_to)
        properties = pika.BasicProperties(app_id='environ', content_type='application/json', reply_to=config['QUEUE']['brainQueue'])
        channel1.basic_publish(exchange='', routing_key=reply_to, body=body, properties=properties)
    elif app_id == 'camera':
        # For camera events just overwrite the latest image
        imgbin = base64.b64decode(body)
        filePath = os.path.join(topdir, 'static/motionImages', reply_to + '.jpg') 
        with open(filePath, 'wb') as f_output:
            f_output.write(imgbin)
        #logger.debug("Saved image to " + filePath )
    elif app_id == 'motion':
        # For motion detection events check the image for any humans
        detectorAPI.doLogic(connection, content, reply_to, body)
    elif app_id == 'voice':
        # For voice events we need to determine intent of the speech and reply accordingly
        voiceAPI.doLogic(content, reply_to, body)
    elif app_id == 'button':
        button.doLogic(content, body, logger, ENVIRON)
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
    if config['DEBUG']['debugBrain'] == 'True':
        logger.level = logging.DEBUG
    else:
        logger.level = logging.INFO
    
    # Setup Environment data to be shared with clients
    #-----------------------------------------------------
    ENVIRON = {}
    ENVIRON["topdir"] = topdir
    ENVIRON["SecureMode"] = False
    ENVIRON["Identify"] = True
    ENVIRON["queueSrvr"] = config['QUEUE']['queueSrvr']
    ENVIRON["queuePort"] = config['QUEUE']['queuePort']
    ENVIRON["queueUser"] = config['QUEUE']['queueUser']
    ENVIRON["queuePass"] = config['QUEUE']['queuePass']
    ENVIRON["brainQueue"] = config['QUEUE']['brainQueue']
    ENVIRON["keepImages"] = config['BRAIN']['keepMotionImages']

    #instatiate code libraries to save time 
    #-----------------------------------------------------
    logger.debug("Loading the code libraries for faster responses ")
    import lib.brain_motion as motion
    detectorAPI = motion.detectorAPI(ENVIRON)
    import lib.brain_voice as voice
    voiceAPI = voice.voiceAPI(ENVIRON)
    import lib.brain_button as button

    # define some variables
    isWWWeb = False		
    isQueue = False

    # test internet connection
    isWWWeb = utils.testInternet(logger, 5, "www.google.com")


    # Try and connect to the message queue
    #------------------------------------------------------
    try:
        credentials = pika.PlainCredentials(config['QUEUE']['queueUser'], config['QUEUE']['queuePass'])
        parameters = pika.ConnectionParameters(config['QUEUE']['queueSrvr'], config['QUEUE']['queuePort'], '/',  credentials)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=config['QUEUE']['brainQueue'])
        isQueue = True
        logger.debug('Connected to Message Queue ' + config['QUEUE']['queueSrvr'])
    except:
        logger.error('Unable to connect to Message Queue ' + config['QUEUE']['queueSrvr'])



    # ---------------------------------------------------------------------------------------
    # kick off website for cam feeds
    # ---------------------------------------------------------------------------------------
    if config['BRAIN']['camFeedsWeb'] == 'True':
        logger.info("Starting web server for camera feeds")
        try:
            import camFeeds
            m = Process(target=camFeeds.runWeb, args=(ENVIRON,))
            m.start()
        except:
            logger.error('Failed to start flask server for camera feeds')
 
   
    # If successful start listening on Central channel 
    #------------------------------------------------------
    if isQueue:
        try:
            logger.debug('Starting to listen on channel ' + config['QUEUE']['brainQueue'])
            channel.basic_consume(queue=config['QUEUE']['brainQueue'], on_message_callback=callback, auto_ack=True)
            channel.start_consuming()
            logger.debug('Now listening on channel ' + config['QUEUE']['brainQueue'])
        except:
            logger.error('Failed to start listening on channel ' + config['QUEUE']['brainQueue'])
    


