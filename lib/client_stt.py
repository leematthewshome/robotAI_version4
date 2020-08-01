#!/usr/bin/python
"""
===============================================================================================
This module is used for turning speech into text (STT)
Author: Lee Matthews 2018 - updated 2020
===============================================================================================
"""

import logging
import time

import tempfile
import wave
import audioop
import pyaudio
import os

import base64
from google.cloud import speech_v1 as speech


# Insert the correct values from your Google project
json_file = 'my-home-ai-project-c6ff7abb0b1a.json'
proj_name = 'my-home-ai-project'


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
    def listen(self, stt=True):
        self.logger.debug("Running stt.listen function with STT = " + str(stt))
        
        _audio = pyaudio.PyAudio()
        RATE = 16000
        CHUNK = 1024
        LISTEN_TIME = 10

        # Set threshold to the current average background noise
        # TODO When have listen sensor working we need to uncomment this and remove the fixed setting
        #THRESHOLD = self.ENVIRON["avg_noise"] 
        THRESHOLD = 1

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

        # Only convert our recording to text with STT engine if we need to
        if stt:
            with tempfile.SpooledTemporaryFile(mode='w+b') as f:
                wav_fp = wave.open(f, 'wb')
                wav_fp.setnchannels(1)
                wav_fp.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
                wav_fp.setframerate(RATE)
                wav_fp.writeframes(b''.join(frames))
                wav_fp.close()
                f.seek(0)
                self.logger.debug("Calling transcribe function now...")
                return self.transcribe(f)         
        


    # Submit recording to Google API to convert to text 
    #---------------------------------------------------------------
    def transcribe(self, fp):
        transcribed = []

        data = fp.read()
        speech_content_bytes = base64.b64encode(data)
        speech_content = speech_content_bytes.decode('utf-8')

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.json_path
        os.environ["GCLOUD_PROJECT"] = proj_name

        config = {'language_code': 'en-US'}
        audio = {'content': data}

        client = speech.SpeechClient()
        result = client.recognize(config, audio)
        print (result)


# Testing script
#-------------------------------------------------------------------------------
if __name__ == '__main__':
    ENVIRON = {}
    ENVIRON["topdir"] = '/home/lee/Downloads/robotAI4'

    mystt = stt(ENVIRON)
    result = mystt.listen(True)




