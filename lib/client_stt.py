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
import json
try:
    from google.cloud import speech_v1 as speech
    from google.protobuf.json_format import MessageToJson
except:
    pass
    
# Toggle settings for respeaker or standard Mic
#==============================================
respeaker = True
#==============================================

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
    def listen(self, myFile):
        self.logger.debug("Running stt.listen function ")
        
        RATE = 16000
        CHUNK = 1024
        LISTEN_TIME = 10
        if respeaker:
            CHANNELS = 2
        else:
            CHANNELS = 1

        # Set threshold to the current average background noise
        # TODO if voiceSensor not running we need another way to calc THRESHOLD
        try:
            THRESHOLD = self.ENVIRON["avg_noise"] 
        except:
            THRESHOLD = 2000

        # prepare recording stream
        p = pyaudio.PyAudio()
        self.logger.debug("Opening pyaudio recording stream")
        stream = p.open(format=pyaudio.paInt16,
                                  channels=CHANNELS,
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
            print('AVG RECORDING LEVEL IS ' + str(average))
            if average < THRESHOLD:
                break

        # save the audio data
        stream.stop_stream()
        stream.close()
        self.logger.debug("Closed pyaudio recording stream")

        # Save the recording to the file handle only if we were given one
        if myFile:
            wav_fp = wave.open(myFile, 'wb')
            wav_fp.setnchannels(CHANNELS)
            wav_fp.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
            wav_fp.setframerate(RATE)
            wav_fp.writeframes(b''.join(frames))
            wav_fp.close()
        self.logger.debug("Returning file to client_voice.listen function")

        return myFile      
        

    def convertMono(self, stereo):
        monofile = os.path.join(ENVIRON["topdir"], 'static/audio/monofile.wav')
        mono = wave.open(monofile, 'wb')
        mono.setparams(stereo.getparams())
        mono.setnchannels(1)
        mono.writeframes(audioop.tomono(stereo.readframes(float('inf')), stereo.getsampwidth(), 1, 1))
        mono.close()
        return monofile


    # Submit recording to Google API to convert to text 
    #---------------------------------------------------------------
    def transcribe(self, fp):
        transcribed = ''

        #convert stereo recording to mono file if required
        stereo = wave.open(fp, 'rb')
        if stereo.getnchannels() > 1:
            self.logger.debug("Recording is stereo, so converting to mono ")
            monofile = self.convertMono(stereo)
            self.logger.debug("Mono file is " + monofile)
            f=open(monofile, 'rb')  
            data = f.read()
            f.close()
        else:
            data = fp.read()
        stereo.close()
        
        self.logger.debug("Converting to base64 and utf-8 ")
        speech_content_bytes = base64.b64encode(data)
        speech_content = speech_content_bytes.decode('utf-8')

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.json_path
        os.environ["GCLOUD_PROJECT"] = proj_name

        config = {'language_code': 'en-US'}
        audio = {'content': data}

        self.logger.debug("Sending details to Google STT API ")
        client = speech.SpeechClient()
        response = client.recognize(config, audio)
        result_json = MessageToJson(response)
        result_json = json.loads(result_json)

        if 'results' in result_json:
            for result in result_json["results"]:
                #transcribed.append(result["alternatives"][0]["transcript"].upper())
                transcribed += result["alternatives"][0]["transcript"].upper() + ' '
        else:
            return ""
            
        self.logger.debug("Transcribed: " + transcribed)
        return transcribed
        



# Testing script that is executed if code run directly
#-------------------------------------------------------------------------------
if __name__ == '__main__':
    import tempfile
    ENVIRON = {}
    ENVIRON["avg_noise"] = 1
    ENVIRON["topdir"] = '/home/pi/robotAI4'

    mystt = stt(ENVIRON)
    tmpFile = tempfile.SpooledTemporaryFile(mode='w+b')
    rec = mystt.listen(tmpFile)
    rec.seek(0)
    response = mystt.transcribe(tmpFile)
    print(response)




