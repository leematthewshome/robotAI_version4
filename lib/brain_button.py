#!/usr/bin/python3
"""
===============================================================================================
Functions used when responding to a button press on Brain
Author: Lee Matthews 2021
===============================================================================================
"""

import lib.common_utils as utils
import os
import json

#---------------------------------------------------------------------------
# Function called by robotAI_brain for this set of logic
#---------------------------------------------------------------------------
def doLogic(content, body, logger, ENVIRON):
    topdir = ENVIRON["topdir"]

    # If we received JSON then get the requested action
    #----------------------------------------------------
    if content == 'application/json':
        logger.debug('JSON received by brain_button')
        try:
            data = json.loads(body.decode("utf-8"))
            audio = data["audio"]
            voice = data["voice"]
            audioFile = os.path.join(topdir, 'static/audio', audio)
            logger.error('Playing audio file ' + audioFile)
            utils.play(audioFile)
        except:
            logger.error('Could not load response as JSON')
    else:
        logger.debug('Unexpected content type received by brain_button')

