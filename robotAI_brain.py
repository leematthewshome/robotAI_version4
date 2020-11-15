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

# import python modules for chatbot
import json 
import numpy as np 
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import load_model

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
# Cache our chatbot model here to speed up response
#---------------------------------------------------------
modelpath = os.path.join(topdir, 'static/MLModels/chatbot')
chatpath  = os.path.join(topdir, 'static/MLModels/chatbot/chatschema.json')

chatmodel = load_model(modelpath)
with open(chatpath) as file:
    chatdata = json.load(file)

training_sentences = []
training_labels = []
for intent in chatdata['intents']:
    for pattern in intent['patterns']:
        training_sentences.append(pattern)
        training_labels.append(intent['tag'])

# encode our list of tags  
encoder = LabelEncoder()
encoder.fit(training_labels)
training_labels = encoder.transform(training_labels)

vocab_size = 20000
embedding_dim = 16
oov_token = "<OOV>"
max_len = 20
trunc_type = 'post'

tokenizer = Tokenizer(num_words=vocab_size, oov_token=oov_token) 
tokenizer.fit_on_texts(training_sentences)


#---------------------------------------------------------
# Various functions
#---------------------------------------------------------

# Function executed when queue message received
# -------------------------------------------------------
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
        logger.debug("Saved image to " + filePath )
    elif app_id == 'motion':
        # For motion detection events check the image for any humans
        import lib.brain_motion as motion
        motion.doLogic(ENVIRON, connection, content, reply_to, body)
    elif app_id == 'voice':
        # For voice events we need to determine intent of the speech and reply accordingly
        import lib.brain_voice as voice
        voice.doLogic(ENVIRON, content, reply_to, body, chatmodel, chatdata, tokenizer, encoder)
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
    if config['QUEUE']['brainQueue']:
        logger.level = logging.DEBUG
    else:
        logger.level = logging.INFO

    # Setup Environment data to be shared with clients
    #-----------------------------------------------------
    ENVIRON = {}
    ENVIRON["topdir"] = topdir
    ENVIRON["queueSrvr"] = config['QUEUE']['queueSrvr']
    ENVIRON["queuePort"] = config['QUEUE']['queuePort']
    ENVIRON["queueUser"] = config['QUEUE']['queueUser']
    ENVIRON["queuePass"] = config['QUEUE']['queuePass']
    ENVIRON["brainQueue"] = config['QUEUE']['brainQueue']

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
    
   
