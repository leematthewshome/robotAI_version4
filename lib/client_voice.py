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
import tempfile 

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
        self.stt = client_stt.stt(ENVIRON)
        
        topdir = ENVIRON["topdir"]
        self.beep_hi = os.path.join(topdir, "static/audio/beep_hi.wav")
        self.beep_lo = os.path.join(topdir, "static/audio/beep_lo.wav")

        # Setup details to access the message queue
        credentials = pika.PlainCredentials(ENVIRON["queueUser"], ENVIRON["queuePass"])
        self.parameters = pika.ConnectionParameters(ENVIRON["queueSrvr"], ENVIRON["queuePort"], '/',  credentials)
        

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
            #if output:
            #    self.logger.debug("Result of cmd was: " + str(output))
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
                            connection = pika.BlockingConnection(self.parameters)
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
                self.logger.debug("Received %s from getYesNo() function" % funct)
            elif funct == "pauseListen":
                resp = self.listen(stt=False)
            else:
                self.logger.debug("No handler for function %s" % funct)
                self.say('Sorry, I dont know what to do about %s' % funct)
        return resp


    # call listen function with beep indicators
    # ------------------------------------------------------
    def listen(self, stt):
        self.ENVIRON["listen"] = False
        self.play(self.beep_hi)    
        tmpFile = tempfile.SpooledTemporaryFile(mode='w+b')
        rec = self.stt.listen(tmpFile)
        self.logger.debug("received result back from listen function")
        rec.seek(0)
        self.play(self.beep_lo)    
        self.ENVIRON["listen"] = True
        self.logger.debug("About to transcribe the recorded data")
        
        # only transcribe if we need to        
        if stt:
            response = self.stt.transcribe(tmpFile)
            return response
        else:
            return stt



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
            
        # fix mention of years
        year_regex = re.compile(r'(\b)(\d\d)([1-9]\d)(\b)')
        text = year_regex.sub('\g<1>\g<2> \g<3>\g<4>', text) 
        
        return text


    # Check for a Yes or No. Allows for one loop if no answer. 
    # TODO use NLP later on to determine positive or negative response
    #---------------------------------------------------------------
    def getYesNo(self, questn):
        self.logger.debug("Running stt.getYesNo function")
        # Listen for a response from the speaker
        resp = self.listen(stt=True)
        # first check for yes or no
        if bool(re.search(r'\bYES\b', resp, re.IGNORECASE)) == True:
            return "YES"
        elif bool(re.search(r'\bNO\b', resp, re.IGNORECASE)) == True:
            return "NO"
        else:
            self.say("Sorry, I did not hear a yes or no. " + questn)
            resp = self.listen(stt=True)
        # second check for yes or no
        if bool(re.search(r'\bYES\b', resp, re.IGNORECASE)) == True:
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
                self.ENVIRON["talking"] = True
                self.logger.info("I have now set self.ENVIRON['talking'] = " + str(self.ENVIRON["talking"]))
                chatList = data["list"]
                self.doChat(chatList)
                self.ENVIRON["talking"] = False
                self.logger.info("I have now set self.ENVIRON['talking'] = " + str(self.ENVIRON["talking"]))
            else:
                self.logger.debug("No logic created yet to handle action = " + action)
        else:
            self.logger.debug("No logic created yet to handle content = " + content)
        
    


# Testing script
#-------------------------------------------------------------------------------
if __name__ == '__main__':

    voice = voice()
    voice.say("THE RAIN IN SPAIN FALLS MAINLY ON THE PLAIN. BUT THE OLIVES ARE DELICIOUS WITH A GLASS OF RED.")
    
    

