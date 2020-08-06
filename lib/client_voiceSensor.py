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
        self.sensitivty = .7
        
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


    #Snowboy signal_handler
    def signal_handler(self, signal, frame):
        self.logger.debug("Snowboy signal_handler tripped. Cleaning up.")
        self.interrupted = True


    # Snowboy interrupt callback function
    def interrupt_callback(self):
        if ENVIRON["listen"] == False:
            self.interrupted = True
        return self.interrupted


    # Function Executed once the trigger keyword is received
    def activeListen(self):
        # AutoLevel - display the current average noise level
        self.logger.debug("Current avg_noise is %s" % self.ENVIRON["avg_noise"] )

        if ENVIRON["listen"] == False:
            self.logger.debug("KEYWORD DETECTED. But we are busy so ignore it")
        else:
            # set system to indicate things are busy
            ENVIRON["listen"] = False
            self.logger.debug("KEYWORD DETECTED. Beginning active listen ")
            input = self.VOICE.listen(stt=True)
            # need to submit recorded to to our intent engine. Just print for now.
            print(input)
            # set listen back to true - rely on client_voice to set to false when busy
            ENVIRON["listen"] = True
            
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
    ENVIRON["topdir"] = '/home/pi/robotAI4'
    ENVIRON["listen"] = True
    ENVIRON["queueSrvr"] = queueSrvr
    ENVIRON["queuePort"] = queuePort
    ENVIRON["queueUser"] = queueUser
    ENVIRON["queuePass"] = queuePass
    ENVIRON["clientName"] = clientName                                  #the name assigned to our client device, eg. FrontDoor

    # Create reference to our voice class
    import client_voice
    VOICE = client_voice.voice(ENVIRON)
    
    doSensor(ENVIRON, VOICE)