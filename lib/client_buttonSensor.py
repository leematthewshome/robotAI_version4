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

# import shared utility finctions
import lib.common_utils as utils

GPIO.setmode(GPIO.BCM)

pin = 12
GPIO.setup(pin, GPIO.IN)


#======================================================
# listenLoop class
#======================================================
class listenLoop(object):

    def __init__(self, ENVIRON, VOICE):
        topdir = ENVIRON["topdir"]
        self.ENVIRON = ENVIRON
        
        # setup logging using the common_utils function
        self.logger = utils.setupLogging(topdir, __name__)

        self.VOICE = VOICE
        self.TOPDIR = ENVIRON["topdir"]

        # Setup details to access the message queue
        credentials = pika.PlainCredentials(ENVIRON["queueUser"], ENVIRON["queuePass"])
        self.parameters = pika.ConnectionParameters(ENVIRON["queueSrvr"], ENVIRON["queuePort"], '/',  credentials)

        
    def buttonListen(self):
        while True:
            i=GPIO.input(pin)
            if i==0:
                #print("Pin is LOW")
                #Send message to the brain to trigger bell ringing
                properties = pika.BasicProperties(app_id='button', content_type='application/json', reply_to=self.ENVIRON["clientName"])
                try:
                    body = '{"audio": "' + self.ENVIRON["buttonAudio"] + '", "voice": "' + self.ENVIRON["buttonVoice"] + '"}'
                    connection = pika.BlockingConnection(self.parameters)
                    channel = connection.channel()
                    channel.basic_publish(exchange='', routing_key='Central', body=body, properties=properties)
                    connection.close()
                except:
                    self.logger.error('An error occurred trying to send doorbell alert to Message Queue ' + self.ENVIRON["queueSrvr"])
                
                #Let the person know what we are doing
                self.VOICE.say("Hi, my name is Meebo. I will let my masters know you are here.")
                time.sleep(1)
            else:
                #print("Pin is HIGH")
                pass
            time.sleep(.1)
    
        
# ==========================================================================
# Function called by main robotAI process to run this sensor
# ==========================================================================
def doSensor(ENVIRON, VOICE):
    loop = listenLoop(ENVIRON, VOICE)
    loop.buttonListen()


