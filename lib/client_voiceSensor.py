#!/usr/bin/env python3
"""
===============================================================================================
Sensor to listen for user input via Snowboy for hotword 
Author: Lee Matthews 2016 modified 2020
Note that only one process at a time can use microphone. Need to ensure snowboy and 
listen are stopped for other utilities to use microphone. ENVIRON["listen"] manages this.

TODO - Nothing atm
===============================================================================================
"""
import logging
import signal
import os
import time
import pika
#allow for running listenloop either in isolation or via robotAI.py
try:
    from lib.snowboy import robotAI_snowboy
except:
    from snowboy import robotAI_snowboy



#======================================================
# listenLoop class
#======================================================
class listenLoop(object):

    def __init__(self, ENVIRON, VOICE):
        debug = True
        self.hotword = 'computer.umdl'
        self.sensitivty = .4
        
        self.ENVIRON = ENVIRON
        self.TOPDIR = ENVIRON["topdir"]
        # set initial value for background noise
        self.ENVIRON["avg_noise"] = 100
        self.VOICE = VOICE

        #Set debug level based on details in config DB
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.level = logging.DEBUG
        else:
            self.logger.level = logging.INFO
        
        #set variable for snowboy
        self.interrupted = False

        # Setup details to access the message queue
        credentials = pika.PlainCredentials(ENVIRON["queueUser"], ENVIRON["queuePass"])
        self.parameters = pika.ConnectionParameters(ENVIRON["queueSrvr"], ENVIRON["queuePort"], '/',  credentials)


    #Snowboy signal_handler
    def signal_handler(self, signal, frame):
        self.logger.debug("Snowboy signal_handler tripped. Cleaning up.")
        self.interrupted = True


    # Snowboy interrupt callback function
    def interrupt_callback(self):
        if self.ENVIRON["listen"] == False:
            self.interrupted = True
        return self.interrupted


    # Function Executed once the trigger keyword is received
    def activeListen(self):
        # AutoLevel - display the current average noise level
        self.logger.debug("Current avg_noise is %s" % self.ENVIRON["avg_noise"] )

        if self.ENVIRON["listen"] == False:
            self.logger.debug("KEYWORD DETECTED. But we are busy so ignore it")
        else:
            # set system to indicate things are busy
            self.ENVIRON["listen"] = False
            self.logger.debug("KEYWORD DETECTED. Beginning active listen ")
            response = self.VOICE.listen(stt=True)
            
            # Submit returned text to our intent engine. Then brain will respond over the msgqueue
            body = '{"action": "getResponse", "text": "' + response + '"}'
            self.logger.debug("About to send this data: " +body)
            connection = pika.BlockingConnection(self.parameters)
            channel1 = connection.channel()
            channel1.queue_declare("Central")
            props = pika.BasicProperties(app_id='voice', content_type='application/json', reply_to=self.ENVIRON["clientName"])
            channel1.basic_publish(exchange='', routing_key='Central', body=body, properties=props)
            connection.close()
            
            # set listen back to true - rely on client_voice to set to false when busy
            self.ENVIRON["listen"] = True
            
        #go back to passive listening once ENVIRON["listen"] indicates it is OK
        self.waitUntilListen()


    # ---------------------------------------------------------------------------------------------------------------
    # This function is called in a loop to listen for hotword
    # - if the Snowboy detector loop is stopped then waitUntilListen is called, which polls ENVIRON Listen 
    #   until we are ready to start detecting hotword again
    # ----------------------------------------------------------------------------------------------------------------
    def passiveListen(self):
        partPath = "lib/snowboy/" + self.hotword 
        MODEL_FILE = os.path.join(self.TOPDIR, partPath)
        self.logger.debug("Hotword path = " + MODEL_FILE)

        #initialise Snowboy 
        signal.signal(signal.SIGINT, self.signal_handler)
        self.detector = robotAI_snowboy.HotwordDetector(MODEL_FILE, sensitivity=self.sensitivty,
                                                       debugLevel=self.logger.level, ENVIRON=self.ENVIRON)
        print('Snowboy is passively listening...')

        # Start the Main Snowboy listening loop
        self.detector.start(detected_callback=self.activeListen,
               interrupt_check=self.interrupt_callback,
               sleep_time=0.03)

        self.detector.terminate()
        self.waitUntilListen()


    # Snowboy cant run while we are busy doing stuff, in case brain needs pyaudio
    # So dont start snowboy until we are ready to begin listening again
    def waitUntilListen(self):
        self.logger.debug("waitUntilListen function is now monitoring the ENVIRON listen variable")
        self.interrupted = False
        while True:
            self.logger.debug("waitUntilListen - listen variable is %s" % str(self.ENVIRON['listen']))
            if self.ENVIRON['listen'] == True:
                self.passiveListen()
            time.sleep(1)




# ==========================================================================
# Function called by main robotAI process to run this sensor
# ==========================================================================
def doSensor(ENVIRON, VOICE):
    loop = listenLoop(ENVIRON, VOICE)
    loop.passiveListen()


    
# **************************************************************************
# This will only be executed when we run the sensor on its own for debugging
# **************************************************************************
if __name__ == "__main__":
    print("******** WARNING ********** Starting client_voiceSensor from __main__ procedure")
    # need code here to setup default variables
    clientName = 'ClientDefault'
    queueSrvr = '192.168.0.50'
    queuePort = 5672
    queueUser = 'guest'
    queuePass = 'guest'

    #set placeholder value for our message queue
    ENVIRON = {}
    ENVIRON["clientName"] = clientName                                      #the name of our client device, eg. FrontDoor
    ENVIRON["topdir"] = '/home/lee/Downloads/robotAI4'
    ENVIRON["listen"] = True
    ENVIRON["motion"] = True                                                #flags whether to run motion sensor
    ENVIRON["queueSrvr"] = queueSrvr
    ENVIRON["queuePort"] = queuePort
    ENVIRON["queueUser"] = queueUser
    ENVIRON["queuePass"] = queuePass
    ENVIRON["secureMode"] = True
    ENVIRON["friendMode"] = True
    ENVIRON["talking"] = False


    # Create reference to our voice class
    import client_voice
    VOICE = client_voice.voice(ENVIRON)
    
    doSensor(ENVIRON, VOICE)

