#!/usr/bin/python3
"""
===============================================================================================
Common functions Used By robotai_brian and robotai_client
Author: Lee Matthews 2020
===============================================================================================
"""
import logging
import sqlite3
import json
import pika
import os

# imports for the ML Chatbot
import numpy as np
from tensorflow.keras.preprocessing.sequence import pad_sequences

# create connection to database
# ----------------------------------------------------------------------------------
def createConn(topdir):
    try:
        dbpath = os.path.join(topdir, 'static/db/robotAI.db')
        conn = sqlite3.connect(dbpath)
    except:
        return None
    return conn


# Send details to the message queue
# ----------------------------------------------------------------------------------
def sendMessage(logger, ENVIRON, reply_to, body):
    try:
        credentials = pika.PlainCredentials(ENVIRON["queueUser"], ENVIRON["queuePass"])
        parameters = pika.ConnectionParameters(ENVIRON["queueSrvr"], ENVIRON["queuePort"], '/',  credentials)
        connection = pika.BlockingConnection(parameters)
        channel1 = connection.channel()
        channel1.queue_declare(reply_to)
        properties = pika.BasicProperties(app_id='voice', content_type='application/json', reply_to=ENVIRON["brainQueue"])
        channel1.basic_publish(exchange='', routing_key=reply_to, body=body, properties=properties)
        connection.close()
    except:
        logger.error('There was an error sending the message to the queue')
        return False
    return True


# Build JSON format to be sent to the message queue
#----------------------------------------------------------------------------------
def buildMessage(logger, response):
    result = {'action': 'chat', 'list': response}
    body = json.dumps(result)
    result = sendMessage(logger, ENVIRON, reply_to, body)
    return body


# ---------------------------------------------------------------------------------
# Fetch a list of statements from the chat bot table
#----------------------------------------------------------------------------------
def getChatPath(chatid='0-GREETA-0'):
    # make 2 part chat IDs match the way 'next' column in DB formatted
    arr = chatid.split('-')
    if len(arr) == 2:
        chatid = '0-' + chatid
    print('Running function getChatPath with chatid: ' + chatid)

    # connect to database and check for valid subscription
    conn = createConn()
    if conn is None:
        print('Could not connect to database. Exiting function.')
        return {}
    else:
        cur = conn.cursor()
        print('Connection to DB established and ready with cursor.')

    # function to build the SQL stmnt
    def buildSQL(table, sCat, iItm):
        SQL = "SELECT text, funct, next FROM " + table + " WHERE Category = '" + sCat + "'"
        if str(iItm) != '0':
            SQL += " AND Item = " + str(iItm)
        else:
            SQL += " ORDER BY RANDOM() LIMIT 1 ;"
        return SQL

    # recursively loop through database to get path
    def chatLoop(chatid):
        list = []
        d = None
        row = chatid.split("-")
        sCat = row[1]
        iItm = row[2]

        # create SQL query (add multiple languages later)
        SQL = buildSQL('ChatText', sCat, iItm)
        try:
            cur.execute(SQL)
            list = cur.fetchall()
        except:
            conn.rollback()

        # insert result into the json data object
        if len(list) > 0:
            d = {'text': list[0][0],
               'funct': list[0][1],
               'next': list[0][2]}
        else:
            d = {'text': 'Something went wrong. I could not find the requested chat entry ', 'funct': '', 'next': ''}
        return d

    # run the chat loop to build up our chat list and then return result
    chatlst = []
    while '|' not in chatid and len(chatid) > 0:
        row = chatLoop(chatid)
        chatlst.append(row)
        try:
            chatid = row['next']
        except:
            chatid = ''

    conn.close()

    return chatlst



#---------------------------------------------------------------------------
# Function called by robotAI_brain for this set of logic
#---------------------------------------------------------------------------
def doLogic(ENVIRON, content, reply_to, body, chatmodel, chatdata, tokenizer, encoder):
    debugOn = True
    action = ""

    # setup logging using the python logging library
    #-----------------------------------------------------
    logging.basicConfig()
    logger = logging.getLogger("brain_voice")
    if debugOn:
        logger.level = logging.DEBUG
    else:
        logger.level = logging.INFO


    # If we received JSON then get the requested action
    #-----------------------------------------------------
    if content == 'application/json':
        logger.debug('JSON received by brain_voice. Decoding...')
        try:
            data = json.loads(body.decode("utf-8"))
            action = data["action"]
        except:
            logger.error('Could not load response as JSON or extract key of "type"')
    elif content == 'audio/wav':
        logger.info('This is a placeholder for our speech to text functionality. If we ever move to the brain.')
        action = "stt"

    logger.debug('Action value is: ' + action)


    # Execute requested VOICE action to execute
    #-----------------------------------------------------
    if action == "getChat":
        # need to fetch the relevant chat text requested
        chatid = data["chatItem"]
        logger.debug('Calling getChatPath function')
        result = getChatPath(chatid)
        # return data to the client device that initiated the request 
        result = {'action': 'chat', 'list': result}
        body = json.dumps(result)
        logger.debug("Sending chat text to : " + reply_to)
        result = sendMessage(logger, ENVIRON, reply_to, body)
        
    elif action == "getResponse":
        # need to get the chat response from the ML Chat model
        max_len = 20
        trunc_type = 'post'
        result = []    
        text = data["text"]
        
        logger.debug('Running prediction for: ' + text)
        predictions = chatmodel.predict(pad_sequences(tokenizer.texts_to_sequences([text]), truncating=trunc_type, maxlen=max_len))[0]
        highest = predictions[np.argmax(predictions)]
        category = encoder.inverse_transform([np.argmax(predictions)]) 
        logger.debug("MLChatBot found " + str(highest) + " percent match to " + str(category))
        if highest > .75:
            for i in chatdata['intents']:
                if i['tag']==category:
                    if len(i['context_set']) > 0:
                        result = getChatPath(i['context_set'])
                    else:
                        response = np.random.choice(i['responses'])
                        response = {'text': response, 'funct': '', 'next': ''}    
                        result.append(response)
        else:
            response = "Sorry, I dont have a suitable response to that"
            response = {'text': response, 'funct': '', 'next': ''}    
            result.append(response)
            logpath = ENVIRON["topdir"]
            logpath  = os.path.join(logpath, 'static/MLModels/chatbot/unhandled.log')
            f = open(logpath, "a")
            f.write(text + "\n")
            f.close()

        # return data to the client device that initiated the request 
        result = {'action': 'chat', 'list': result}
        body = json.dumps(result)
        logger.debug("Sending chat text to : " + reply_to)
        result = sendMessage(logger, ENVIRON, reply_to, body)
    else:
        # catch all if we didnt expect the action or was blank
        logger.warning('The action value of ' + action + ' has no code to handle it.')



