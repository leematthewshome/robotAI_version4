#!/usr/bin/python3
"""
===============================================================================================
Main code module for RobotAI Central Brain
Does the heavy thinking on behalf of the RobotAI clients. 
Author: Lee Matthews 2020
===============================================================================================
"""
#import essential python modules
import pika
import time
import socket
import logging
import json
import base64

import client.objectDetector as detector
# TODO we can avoid using cv2 once we send frame dynamically
import cv2


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

# Function to check if we can access the internet
def testInternet(server="www.google.com"):
    logger.debug("Checking network connection to server '%s'...", server)
    try:
        # see if we can resolve the host name -- tells us if there is a DNS listening
        host = socket.gethostbyname(server)
        # connect to the host -- tells us if the host is actually reachable
        socket.create_connection((host, 80), 2)
    except Exception:
        logger.warning("Internet does not seem to be available")
        return False
    else:
        logger.debug("Internet connection working")
        return True


# Function executed when queue message received
# TODO This function needs to pass off processing to sub routines based on app_id 
def callback(ch, method, properties, body):
    try:
        app_id = properties.app_id
        content = properties.content_type
        reply_to = properties.reply_to
        print("Message received from "+reply_to+" App: "+app_id+" content: "+content)
    except:
        logger.warning("Not all expected properties available")
    
    if app_id == 'motion' and content == 'image/jpg':
        
        imgbin = base64.b64decode(body)
        with open('captured.jpg', 'wb') as f_output:
            f_output.write(imgbin)
        print("saved file")
        
        # use Machine learning to determine if a person exists in the image
        # TODO detector currently hard coded to use file from disk. should be able to just pass imgbin
        frame = cv2.imread('captured.jpg')
        dt = detector.detectorAPI()
        result = dt.objectCount(frame)
        print(result)


        # then asses the faces in the image to see if we recognize



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
    ENVIRON["SecureMode"] = False
    ENVIRON["Identify"] = True

    # define some variables
    isWWWeb = False		
    isQueue = False

    # try to connect to internet a number of times
    #-----------------------------------------------------
    tries = 5
    while tries > 0 and isWWWeb == False:
        isWWWeb = testInternet()
        if isWWWeb == False:
            tries = tries - 1
            time.sleep(3)
    if not isWWWeb:
        logger.error('Unable to connect to Message Queue ' + queueSrvr)


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
    
   
