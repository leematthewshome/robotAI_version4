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

import wave
import audioop
import pyaudio



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
                self.logger.debug("Received %s from getYesNo() function" % funct)
            elif funct == "pauseListen":
                resp = self.listen(stt=False)
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
            

    
    # function to get sound level score
    #---------------------------------------------------------------
    def getScore(self, data):
        rms = audioop.rms(data, 2)
        score = rms 
        return score



    # Placeholder for function to listen for speech. 
    #---------------------------------------------------------------
    def listen(self, stt):
        self.logger.debug("Running stt.listen function ")
        self.play(self.beep_hi)    
        
        _audio = pyaudio.PyAudio()
        RATE = 16000
        CHUNK = 1024
        LISTEN_TIME = 10

        # Set threshold to the current average background noise
        # TODO if voiceSensor not running we need another way to calc THRESHOLD
        try:
            THRESHOLD = self.ENVIRON["avg_noise"] 
        except:
            THRESHOLD = 100

        # prepare recording stream
        self.logger.debug("Opening pyaudio recording stream")
        stream = _audio.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=RATE,
                                  input=True,
                                  frames_per_buffer=CHUNK)
        frames = []

        # waitVal determines the pause before a command is expected. (A value of 10 is around 1 second)
        waitVal = 30
        lastN = [THRESHOLD * waitVal for i in range(waitVal)]

        for i in range(0, int(RATE / CHUNK * LISTEN_TIME)):
            data = stream.read(CHUNK)
            frames.append(data)
            score = self.getScore(data)
            lastN.pop(0)
            lastN.append(score)
            average = sum(lastN) / float(len(lastN))

            #If average sound level is below cutoff then we have silence, so stop listening
            if average < THRESHOLD:
                break

        # save the audio data
        stream.stop_stream()
        stream.close()
        self.logger.debug("Closed pyaudio recording stream")
        self.play(self.beep_lo)    

        # Save the recording to file and transcribe only if required
        # TODO Do we even need to put in a file????????????????????
        if stt:
            with tempfile.SpooledTemporaryFile(mode='w+b') as myFile:
                wav_fp = wave.open(myFile, 'wb')
                wav_fp.setnchannels(1)
                wav_fp.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
                wav_fp.setframerate(RATE)
                wav_fp.writeframes(b''.join(frames))
                wav_fp.close()
                myFile.seek(0)
                self.logger.debug("Sending recording to brain for STT and intent")
                
                # send data to brain and response will be posted to message queue 
                #self.stt.transcribe(myFile)
                wavData = myFile.read()
                try:
                    properties = pika.BasicProperties(app_id='voice', content_type='audio/wav', reply_to=self.ENVIRON["clientName"])
                    before = datetime.datetime.today()
                    connection = pika.BlockingConnection(self.parameters)
                    channel = connection.channel()
                    channel.basic_publish(exchange='', routing_key='Central', body=wavData, properties=properties)
                    connection.close()
                    after = datetime.datetime.today()
                    self.logger.info("Time taken: " + str(after-before))                 
                except:
                    self.logger.error('Unable to send recording to Message Queue ')

        else:
            return None
                    
                    
                            
    # General function to work out what to do from 'action' 
    # ------------------------------------------------------
    def doLogic(self, content, body):
        if content == 'application/json':
            data = json.loads(body.decode("utf-8"))
            action = data["action"]
            if action == 'chat':
                self.ENVIRON["talking"] = True
                chatList = data["list"]
                self.doChat(chatList)
                self.ENVIRON["talking"] = False
            else:
                self.logger.debug("No logic created yet to handle action = " + action)
        else:
            self.logger.debug("No logic created yet to handle content = " + content)
        
    


# Testing script
#-------------------------------------------------------------------------------
if __name__ == '__main__':

    voice = voice()
    voice.say("THE RAIN IN SPAIN FALLS MAINLY ON THE PLAIN. BUT THE OLIVES ARE DELICIOUS WITH A GLASS OF RED.")
    
    
