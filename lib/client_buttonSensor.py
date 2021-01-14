#!/usr/bin/env python3
"""
===============================================================================================
Sensor to listen for user input via button press 
Author: Lee Matthews 2021

TODO - Nothing atm
===============================================================================================
"""
import logging
import pika
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

pin = 12
GPIO.setup(pin, GPIO.IN)


#======================================================
# listenLoop class
#======================================================
class listenLoop(object):

    def __init__(self, ENVIRON, VOICE):
        debug = True
        self.ENVIRON = ENVIRON
        self.VOICE = VOICE
        self.TOPDIR = ENVIRON["topdir"]

        #Set debug level based on details in config DB
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.level = logging.DEBUG
        else:
            self.logger.level = logging.INFO
        
        # Setup details to access the message queue
        credentials = pika.PlainCredentials(ENVIRON["queueUser"], ENVIRON["queuePass"])
        self.parameters = pika.ConnectionParameters(ENVIRON["queueSrvr"], ENVIRON["queuePort"], '/',  credentials)

        
    def buttonListen(self):
        while True:
            i=GPIO.input(pin)
            if i==0:
                print("Pin is LOW")
                self.VOICE.say("You pressed the button")
                time.sleep(1)
            else:
                print("Pin is HIGH")
            time.sleep(.1)
    
        
# ==========================================================================
# Function called by main robotAI process to run this sensor
# ==========================================================================
def doSensor(ENVIRON, VOICE):
    loop = listenLoop(ENVIRON, VOICE)
    loop.buttonListen()

