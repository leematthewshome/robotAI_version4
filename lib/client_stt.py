#!/usr/bin/python
"""
===============================================================================================
This module is used for turning speech into text (STT)
Author: Lee Matthews 2018 - updated 2020
===============================================================================================
"""

import logging
import time


# Speech to text class. We will use an external engine (google?) for stt operations
#---------------------------------------------------------------------------------------------
class stt():

    def __init__(self):
        debugOn = True
        logging.basicConfig()
        self.logger = logging.getLogger("stt")
        if debugOn:
            self.logger.level = logging.DEBUG
        else:
            self.logger.level = logging.INFO

        
    # Placeholder for function to listen for speech. 
    # TODO create proper function to record and send to stt
    #---------------------------------------------------------------
    def listen(self, stt=True):
        self.logger.debug("Running stt.listen function")
        # record speech from microphone
        resp = ""
        # send to stt engine to be translated to text
        if stt:
            resp = ["WHATEVER"]
            
        time.sleep(5)
        return resp            



    


