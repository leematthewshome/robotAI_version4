#!/usr/bin/python
"""
===============================================================================================
This module is used for turning speech into text (STT)
Author: Lee Matthews 2018
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


# Voice class. Handles text to speech (tts) and speech to text (stt)
#---------------------------------------------------------------------------------------------
class voice():

    def __init__(self, language="en-US"):
        self.language = language
        logging.basicConfig()
        self.logger = logging.getLogger("voice")
        self.logger.setLevel(logging.DEBUG)

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
                """
                nText = row['next']
                if '|' in nText:
                    options = nText.split("|")
                    for item in options:
                        row = item.split("-")
                        rtxt = row[0]
                        if rtxt.upper() in resp:
                            self.doChat(item)
               """


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
                resp = self.say("Need yes no function")
            elif funct == "pauseListen":
                resp = self.say("Need pause listen function")
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

    tts = voice()
    tts.say("THE RAIN IN SPAIN FALLS MAINLY ON THE PLAIN. BUT THE OLIVES ARE DELICIOUS WITH A GLASS OF RED.")
