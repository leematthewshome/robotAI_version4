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
import json 
import numpy as np
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import load_model


#-------------------------------------------------------------------------------------------------------------------------
# Object Detection detector
#-------------------------------------------------------------------------------------------------------------------------
class voiceAPI:

    def __init__(self, ENVIRON):
        debugOn = True

        # setup logging based on level
        logging.basicConfig()
        logger = logging.getLogger("brain_voice")
        if debugOn:
            logger.level = logging.DEBUG
        else:
            logger.level = logging.INFO
        self.logger = logger
        
        self.ENVIRON = ENVIRON

        # Check for chat database
        #-----------------------------------------------------
        dbpath = os.path.join(self.ENVIRON["topdir"], 'static/db/robotAI.db')
        if not os.path.isfile(dbpath):
            self.buildDB()

        # cache AI chatbot components to speed things up
        #--------------------------------------------------
        vocab_size = 20000
        embedding_dim = 16
        oov_token = "<OOV>"
        max_len = 20
        trunc_type = 'post'
        modelpath = os.path.join(self.ENVIRON["topdir"], 'static/MLModels/chatbot')
        chatpath  = os.path.join(self.ENVIRON["topdir"], 'static/MLModels/chatbot/chatschema.json')
        self.chatmodel = load_model(modelpath)
        with open(chatpath) as file:
            self.chatdata = json.load(file)

        training_sentences = []
        training_labels = []
        for intent in self.chatdata['intents']:
            for pattern in intent['patterns']:
                training_sentences.append(pattern)
                training_labels.append(intent['tag'])

        # encode our list of tags  
        self.encoder = LabelEncoder()
        self.encoder.fit(training_labels)
        training_labels = self.encoder.transform(training_labels)

        self.tokenizer = Tokenizer(num_words=vocab_size, oov_token=oov_token) 
        self.tokenizer.fit_on_texts(training_sentences)


    # create connection to database
    # ----------------------------------------------------------------------------------
    def createConn(self):
        try:
            dbpath = os.path.join(self.ENVIRON["topdir"], 'static/db/robotAI.db')
            conn = sqlite3.connect(dbpath)
        except:
            return None
        return conn


    # build new chat database
    # ----------------------------------------------------------------------------------
    def buildDB(self):
        self.logger.warning("Warning: No ChatText DB found. Creating now... ")
        import csv
        conn = self.createConn()
        # now create tables and populate from CSV
        cur = conn.cursor() 
        cur.execute("""CREATE TABLE ChatText (category VARCHAR(32) NOT NULL, item INTEGER NOT NULL, text VARCHAR(255), funct VARCHAR(255), next VARCHAR(255))""")
        cur.execute("""CREATE INDEX ChatText_cat ON ChatText(category)""")
        cur.execute("""CREATE INDEX ChatText_catitem ON ChatText(category, item)""")
        csvpath = os.path.join(self.ENVIRON["topdir"], 'static/db/ChatText.csv')
        with open(csvpath, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                data = (row['category'], row['item'], row['text'], row['funct'], row['next'])
                cur.execute("INSERT INTO ChatText VALUES (?,?,?,?,?);", data)
        conn.commit()
        self.logger.warning("ChatText DB was successfully created from CSV. ")
        conn.close()


    # Send details to the message queue
    # ----------------------------------------------------------------------------------
    def sendMessage(self, reply_to, body):
        try:
            credentials = pika.PlainCredentials(self.ENVIRON["queueUser"], self.ENVIRON["queuePass"])
            parameters = pika.ConnectionParameters(self.ENVIRON["queueSrvr"], self.ENVIRON["queuePort"], '/',  credentials)
            connection = pika.BlockingConnection(parameters)
            channel1 = connection.channel()
            channel1.queue_declare(reply_to)
            properties = pika.BasicProperties(app_id='voice', content_type='application/json', reply_to=self.ENVIRON["brainQueue"])
            channel1.basic_publish(exchange='', routing_key=reply_to, body=body, properties=properties)
            connection.close()
        except:
            self.logger.error('There was an error sending the message to the queue')
            return False
        return True


    # Build JSON format to be sent to the message queue
    #----------------------------------------------------------------------------------
    def buildMessage(self, response):
        result = {'action': 'chat', 'list': response}
        body = json.dumps(result)
        result = self.sendMessage(reply_to, body)
        return body


    # ---------------------------------------------------------------------------------
    # Fetch a list of statements from the chat bot table
    #----------------------------------------------------------------------------------
    def getChatPath(self, chatid='0-GREETA-0'):
        # make 2 part chat IDs match the way 'next' column in DB formatted
        arr = chatid.split('-')
        if len(arr) == 2:
            chatid = '0-' + chatid
        self.logger.debug('Running function getChatPath with chatid: ' + chatid)

        # connect to database and check for valid subscription
        conn = self.createConn()
        if conn is None:
            self.logger.error('Could not connect to database. Exiting function.')
            return {}
        else:
            cur = conn.cursor()

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
    def doLogic(self, content, reply_to, body):
        debugOn = True
        action = ""

        # If we received JSON then get the requested action
        #-----------------------------------------------------
        if content == 'application/json':
            self.logger.debug('JSON received by brain_voice. Decoding...')
            try:
                data = json.loads(body.decode("utf-8"))
                action = data["action"]
            except:
                self.logger.error('Could not load response as JSON or extract key of "type"')
        elif content == 'audio/wav':
            self.logger.info('This is a placeholder for our speech to text functionality. If we ever move to the brain.')
            action = "stt"
        self.logger.debug('Action value is: ' + action)


        # Execute requested VOICE action to execute
        #-----------------------------------------------------
        if action == "getChat":
            # need to fetch the relevant chat text requested
            chatid = data["chatItem"]
            self.logger.debug('Calling getChatPath function for ' + chatid)
            result = self.getChatPath(chatid)
            # return data to the client device that initiated the request 
            result = {'action': 'chat', 'list': result}
            body = json.dumps(result)
            self.logger.debug("Sending chat text to : " + reply_to)
            result = self.sendMessage(reply_to, body)
        
        elif action == "getResponse":
            # need to get the chat response from the ML Chat model
            max_len = 20
            trunc_type = 'post'
            result = []    
            text = data["text"]
        
            self.logger.debug('Running prediction for: ' + text)
            predictions = self.chatmodel.predict(pad_sequences(self.tokenizer.texts_to_sequences([text]), truncating=trunc_type, maxlen=max_len))[0]
            highest = predictions[np.argmax(predictions)]
            category = self.encoder.inverse_transform([np.argmax(predictions)]) 
            self.logger.debug("MLChatBot found " + str(highest) + " percent match to " + str(category))
            if highest > .75:
                for i in self.chatdata['intents']:
                    if i['tag']==category:
                        if len(i['context_set']) > 0:
                            result = self.getChatPath(i['context_set'])
                        else:
                            response = np.random.choice(i['responses'])
                            response = {'text': response, 'funct': '', 'next': ''}    
                            result.append(response)
            else:
                response = "Sorry, I dont have a suitable response to that"
                response = {'text': response, 'funct': '', 'next': ''}    
                result.append(response)
                logpath  = os.path.join(self.ENVIRON["topdir"], 'static/MLModels/chatbot/unhandled.log')
                f = open(logpath, "a")
                f.write(text + "\n")
                f.close()

            # return data to the client device that initiated the request 
            result = {'action': 'chat', 'list': result}
            body = json.dumps(result)
            self.logger.debug("Sending chat text to : " + reply_to)
            result = self.sendMessage(reply_to, body)
        else:
            # catch all if we didnt expect the action or was blank
            self.logger.warning('The action value of ' + action + ' has no code to handle it.')




