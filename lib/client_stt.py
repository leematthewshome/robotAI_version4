#!/usr/bin/python
"""
===============================================================================================
This module is used for turning speech into text (STT)
Author: Lee Matthews 2018 - updated 2020
===============================================================================================
"""

import logging
import time
import pika
import base64
import datetime
"""
import wave
import audioop
import pyaudio
import os
"""



# Speech to text class. We will use an external engine (google?) for stt operations
#---------------------------------------------------------------------------------------------
class stt():

    def __init__(self, ENVIRON):
        debugOn = True
        logging.basicConfig()
        self.logger = logging.getLogger("stt")
        if debugOn:
            self.logger.level = logging.DEBUG
        else:
            self.logger.level = logging.INFO

        self.ENVIRON = ENVIRON

        # Setup details to access the message queue
        credentials = pika.PlainCredentials(ENVIRON["queueUser"], ENVIRON["queuePass"])
        self.parameters = pika.ConnectionParameters(ENVIRON["queueSrvr"], ENVIRON["queuePort"], '/',  credentials)
        
    """
        path = ENVIRON["topdir"]
        self.json_path = os.path.join(path, 'static/google', json_file)


    # function to get sound level score
    #---------------------------------------------------------------
    def getScore(self, data):
        rms = audioop.rms(data, 2)
        score = rms 
        return score

        
    # Placeholder for function to listen for speech. 
    # TODO create proper function to record and send to stt
    #---------------------------------------------------------------
    def listen(self, myFile):
        self.logger.debug("Running stt.listen function ")
        
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

        # Save the recording to the file handle only if we were given one
        if myFile:
            wav_fp = wave.open(myFile, 'wb')
            wav_fp.setnchannels(1)
            wav_fp.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
            wav_fp.setframerate(RATE)
            wav_fp.writeframes(b''.join(frames))
            wav_fp.close()
        self.logger.debug("Returning file to client_voice.listen function")

        return myFile      
    """     


    def transcribe(self, fp):
        wavData = fp.read()
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






# Testing script that is executed if code run directly
#-------------------------------------------------------------------------------
if __name__ == '__main__':
    ENVIRON = {}
    ENVIRON["avg_noise"] = 1
    ENVIRON["topdir"] = '/home/lee/Downloads/robotAI4'

    mystt = stt(ENVIRON)
    result = mystt.listen(True)
    print(result)




