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


# Voice class. Handles text to speech (tts) and speech to text (stt)
#---------------------------------------------------------------------------------------------
class voice():

    def __init__(self, language="en-US"):
        self.language = language
        logging.basicConfig()
        self.logger = logging.getLogger("TTS")
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



# Testing script
#-------------------------------------------------------------------------------
if __name__ == '__main__':

    tts = voice()
    tts.say("THE RAIN IN SPAIN FALLS MAINLY ON THE PLAIN. BUT THE OLIVES ARE DELICIOUS WITH A GLASS OF RED.")