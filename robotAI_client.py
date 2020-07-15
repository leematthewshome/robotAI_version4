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
import time
import logging
import socket
from multiprocessing import Process, Manager, Queue


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
def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)



#---------------------------------------------------------
#Kick off sensor functions in separate processes
#---------------------------------------------------------
if __name__ == '__main__':

    # setup logging using the python logging library
    logging.basicConfig()
    logger = logging.getLogger("robotAI_client")
    logger.level = logging.DEBUG

    # Setup Environment data to be shared with Sensors
    #------------------------------------------------------
    mgr = Manager()
    ENVIRON = mgr.dict()
    ENVIRON["queueSrvr"] = queueSrvr
    ENVIRON["queuePort"] = queuePort
    ENVIRON["queueUser"] = queueUser
    ENVIRON["queuePass"] = queuePass
    ENVIRON["clientName"] = clientName                      #the name assigned to our client device, eg. FrontDoor
    ENVIRON["motion"] = True                                #flags whether to run motion sensor
    # these should be sent from central on connect
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

    
    # ---------------------------------------------------------------------------------------
    # kick off motion sensor process based on enabled = TRUE
    # ---------------------------------------------------------------------------------------
    if motionSensor:
        try:
            from client import motionSensor
            m = Process(target=motionSensor.doSensor, args=(ENVIRON, ))
            m.start()
        except:
            logger.error('Failed to start motion sensor')
    

    # ---------------------------------------------------------------------------------------
    # Send connect message to Central channel and Start listening on our client channel 
    # ---------------------------------------------------------------------------------------
    if isQueue:
        properties = pika.BasicProperties(app_id='connect', content_type='text', reply_to=clientName)
        body =  clientName 
        channel.basic_publish(exchange='', routing_key='Central', body=body, properties=properties)
        channel.queue_declare(queue=clientName)
        try:
            logger.debug('Starting to listen on channel ' + clientName)
            channel.basic_consume(queue=clientName, on_message_callback=callback, auto_ack=True)
            channel.start_consuming()
            logger.debug('Now listening on channel ' + clientName)
        except:
            logger.error('Failed to start listening on channel ' + clientName)
    
 
