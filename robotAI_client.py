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
import configparser

# import shared utility finctions
from lib import common_utils as utils
from lib import client_voice


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
            if key != 'topdir':
                ENVIRON[key] = data[key]
    elif app_id == 'motion':
        # call our set of actions related to motion
        import lib.client_motion as motion
        motion.doLogic(ENVIRON, VOICE, connection, logger, content, reply_to, body)
    elif app_id == 'voice':
        # call the set of actions related to voice
        VOICE.doLogic(content, body)
    else:
        logger.error("Message received from "+reply_to+" but no logic exists for "+app_id)



#---------------------------------------------------------
#Kick off sensor functions in separate processes
#---------------------------------------------------------
if __name__ == '__main__':

    # setup logging using the common_utils function
    utils.setupLogging(topdir, 'robotAI_client')

    # Setup Environment data to be shared with Sensors
    #------------------------------------------------------
    mgr = Manager()
    ENVIRON = mgr.dict()
    ENVIRON["queueSrvr"] = config['QUEUE']['queueSrvr']
    ENVIRON["queuePort"] = config['QUEUE']['queuePort']
    ENVIRON["queueUser"] = config['QUEUE']['queueUser']
    ENVIRON["queuePass"] = config['QUEUE']['queuePass']
    ENVIRON["clientName"] = config['CLIENT']['clientName']              # the name assigned to our client device, eg. FrontDoor
    ENVIRON["motion"] = config['CLIENT']['motionSensor']                # flags whether to run motion sensor
    ENVIRON["listen"] = True                                            # indicates pyaudio is free for hotword detection
    ENVIRON["topdir"] = topdir
    ENVIRON["buttonAudio"] = config['CLIENT']['buttonAudio']              # the audio file triggered on brain when button pressed
    ENVIRON["buttonVoice"] = config['CLIENT']['buttonVoice']              # the words spoken on brain when button is pressed
    # these defaults will be updated from central on connect
    ENVIRON["secureMode"] = config['CLIENT']['secureMode']
    ENVIRON["friendMode"] = config['CLIENT']['friendMode']
    ENVIRON["talking"] = False			 

    # Create reference to our voice class
    VOICE = client_voice.voice(ENVIRON, logger)

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
        channel.queue_declare(queue=config['CLIENT']['clientName'])
        isQueue = True
        logger.debug('Connected to Message Queue ' + config['QUEUE']['queueSrvr'])
    except:
        logger.error('Unable to connect to Message Queue ' + config['QUEUE']['queueSrvr'])

    
    # ---------------------------------------------------------------------------------------
    # kick off motion sensor process based on enabled = TRUE
    # ---------------------------------------------------------------------------------------
    if config['CLIENT']['motionSensor'] == "True":
        logger.info("Starting motion sensor")
        try:
            from lib import client_motionSensorPi
            m = Process(target=client_motionSensorPi.doSensor, args=(ENVIRON, ))
            m.start()
        except:
            logger.error('Failed to start motion sensor')
    


    # ---------------------------------------------------------------------------------------
    # kick off voice sensor process based on enabled = TRUE
    # ---------------------------------------------------------------------------------------
    if config['CLIENT']['voiceSensor'] == "True":
        logger.info("Starting voice sensor")
        try:
            from lib import client_voiceSensor
            m = Process(target=client_voiceSensor.doSensor, args=(ENVIRON, VOICE,))
            m.start()
        except:
            logger.error('Failed to start voice sensor')
    
    

    # ---------------------------------------------------------------------------------------
    # kick off button sensor process based on enabled = TRUE
    # ---------------------------------------------------------------------------------------
    if config['CLIENT']['buttonSensor'] == "True":
        logger.info("Starting button sensor")
        try:
            from lib import client_buttonSensor
            m = Process(target=client_buttonSensor.doSensor, args=(ENVIRON, VOICE,))
            m.start()
        except:
            logger.error('Failed to start button sensor')
    
    
    # ---------------------------------------------------------------------------------------
    # Send connect message to Central channel and Start listening on our client channel 
    # ---------------------------------------------------------------------------------------
    if isQueue:
        logger.info("Sending connection message to message queue")
        properties = pika.BasicProperties(app_id='connect', content_type='text', reply_to=config['CLIENT']['clientName'])
        body = config['QUEUE']['queueSrvr'] 
        channel.basic_publish(exchange='', routing_key=config['QUEUE']['brainQueue'], body=body, properties=properties)
        channel.queue_declare(queue=config['QUEUE']['queueSrvr'])

        try:
            logger.debug('Starting to listen on channel ' + config['QUEUE']['queueSrvr'])
            channel.basic_consume(queue=config['CLIENT']['clientName'], on_message_callback=callback, auto_ack=True)
            channel.start_consuming()
        except:
            logger.error('Failed to start listening on channel ' + config['QUEUE']['queueSrvr'])

 
