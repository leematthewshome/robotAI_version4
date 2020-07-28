#!/usr/bin/python
"""
===============================================================================================
This module is used for various voice operations
Author: Lee Matthews 2018 - updated 2020
===============================================================================================
"""

import os
import tempfile
import subprocess
import logging
import json
import re
import time
import datetime
import pika

# import from different points to allow for direct test
try:
    import lib.client_stt as client_stt
except:
    import client_stt



#---------------------------------------------------------------------------------------------
# Voice class. Handles text to speech (tts) and speech to text (stt)
#---------------------------------------------------------------------------------------------
class voice():

    def __init__(self, ENVIRON, language="en-US"):
        debugOn = True
        logging.basicConfig()
        self.logger = logging.getLogger("voice")
        if debugOn:
            self.logger.level = logging.DEBUG
        else:
            self.logger.level = logging.INFO

        self.ENVIRON = ENVIRON
        self.language = language
        self.stt = client_stt.stt()


    # Text to speech using Pico2Wave - the most human sounding voice
    #---------------------------------------------------------------
    def say(self, phrase):
        #Pico speaks sentence case better than capitals
        phrase = phrase.capitalize()
        self.logger.debug("Saying " + phrase + " with Pico2Wave")

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            fname = f.name
        cmd = ['pico2wave', '--wave', fname]
        cmd.extend(['-l', self.language])
        cmd.append(phrase)

        with tempfile.TemporaryFile() as f:
            subprocess.call(cmd, stdout=f, stderr=f)
            f.seek(0)
            output = f.read()
            if output:
                self.logger.debug("Result of cmd was: " + str(output))
        self.play(fname)
        os.remove(fname)


    # Play a WAV file using aplay
    #---------------------------------------------------------------
    def play(self, filename):
        cmd = ['aplay', str(filename)]
        with tempfile.TemporaryFile() as f:
            subprocess.call(cmd, stdout=f, stderr=f)
            f.seek(0)
            output = f.read()
            if output:
                self.logger.debug("Result of cmd was: " + str(output))



    # loop through the chat sequence and say the text
    # ------------------------------------------------------
    def doChat(self, chatList):
        if not chatList or len(chatList) == 0:
            self.say('Sorry, I could not work out what to say.')
        else:
            # loop through each item in the chat text returned
            for row in chatList:
                resp = self.doChatItem(row['text'], row['funct'])
                # if we need to select a path then loop through all options and search for response
                nText = row['next']
                if '|' in nText:
                    options = nText.split("|")
                    for item in options:
                        row = item.split("-")
                        rtxt = row[0]
                        if rtxt.upper() in resp:
                            # Request chat data from brain
                            body = '{"action": "getChat", "chatItem": "' + item + '"}'
                            self.logger.debug("About to send this data: " +body)
                            credentials = pika.PlainCredentials(self.ENVIRON["queueUser"], self.ENVIRON["queuePass"])
                            parameters = pika.ConnectionParameters(self.ENVIRON["queueSrvr"], self.ENVIRON["queuePort"], '/',  credentials)
                            connection = pika.BlockingConnection(parameters)
                            channel1 = connection.channel()
                            channel1.queue_declare("Central")
                            props = pika.BasicProperties(app_id='voice', content_type='application/json', reply_to=self.ENVIRON["clientName"])
                            channel1.basic_publish(exchange='', routing_key='Central', body=body, properties=props)
                            connection.close()
       

    # handle (eg. say) a single chat item
    # ------------------------------------------------------
    def doChatItem(self, text, funct):
        self.logger.debug("running doChatItem for function %s and text '%s'" % (funct, text))
        resp = ''
        # if the text is "wait(xx)" where xx is an integer then wait for that time (in seconds)
        if re.search(r'^wait\([0-9]+\)$', text) is not None:
            text = text.upper()
            text = text.replace('WAIT(', '').replace(')', '')
            num = int(text)
            time.sleep(num)
        else:
            text = self.enrichText(text)
            self.say(text)
        # if there is a function mentioned run it and get the results
        if funct:
            funct = funct.strip()
            if funct == "yesNo":
                resp = self.getYesNo(text)
            elif funct == "pauseListen":
                resp = self.stt.listen(stt=False)
            else:
                self.logger.debug("No handler for function %s" % funct)
                self.say('Sorry, I dont know what to do about %s' % funct)
        return resp


    # update the chat text with any context sensitive values
    # ------------------------------------------------------
    def enrichText(self, text):
        # replace the keyword 'dayPart' with relevant replacement
        if 'dayPart' in text:
            now = datetime.datetime.now()
            hour = now.hour
            if hour < 12:
                dayPart = "Morning"
            elif hour < 18:
                dayPart = "Afternoon"
            else:
                dayPart = "Evening"
            text = text.replace('dayPart', dayPart)
        return text


    # Check for a Yes or No. Allows for one loop if no answer. 
    # TODO use NLP later on to determine positive or negative response
    #---------------------------------------------------------------
    def getYesNo(self, questn):
        self.logger.debug("Running stt.getYesNo function")
        # function to see if the response contained yes
        def getResponse(texts):
            str = ""
            for text in texts:
                str += text
            return str

        # Listen for a response from the speaker
        texts = self.stt.listen(stt=True)
        # if no response was received we get an error so use try block
        try:
            resp = getResponse(texts)
        except:
            resp = "WHATEVER"
        # first check for yes or no
        if bool(re.search(r'\byes\b', resp, re.IGNORECASE)) == True:
            return "YES"
        elif bool(re.search(r'\bno\b', resp, re.IGNORECASE)) == True:
            return "NO"
        else:
            self.say("Sorry, I did not hear a yes or no. " + questn)
            texts = self.stt.listen(stt=True)
            try:
                resp = getResponse(texts)
            except:
                resp = "WHATEVER"
        # second check for yes or no
        if bool(re.search(r'\byes\b', resp, re.IGNORECASE)) == True:
            return "YES"
        else:
            return "NO"
    
                            
    # General function to work out what to do from 'action' 
    # ------------------------------------------------------
    def doLogic(self, content, body):
        if content == 'application/json':
            data = json.loads(body.decode("utf-8"))
            action = data["action"]
            if action == 'chat':
                chatList = data["list"]
                self.doChat(chatList)
            else:
                self.logger.debug("No logic created yet to handle action = " + action)
        else:
            self.logger.debug("No logic created yet to handle content = " + content)
        
    


# Testing script
#-------------------------------------------------------------------------------
if __name__ == '__main__':

    voice = voice()
    voice.say("THE RAIN IN SPAIN FALLS MAINLY ON THE PLAIN. BUT THE OLIVES ARE DELICIOUS WITH A GLASS OF RED.")
