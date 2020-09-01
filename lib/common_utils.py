#!/usr/bin/python3
"""
===============================================================================================
Common functions Used By robotai_brian and robotai_client
Author: Lee Matthews 2020
===============================================================================================
"""
import time


import configparser

def setVariables(section):
    config = configparser.ConfigParser()
    config.sections()
    config.read('/home/lee/Downloads/robotAI4/settings.ini')
    data = dict(config.items(section))
    for key in data:
        print('global ' + key)
        exec('global ' + key)
        exec(key + ' = ' + data[key])
    
    
# Function to check if we can access the internet
def testInternet(logger, tries, server="www.google.com"):
    import socket
    count = 1
    while count <= tries:
        logger.debug("Trying " + str(count) + " time(s) to connect to " + server)
        try:
            # try to resolve host name then connect with socket
            host = socket.gethostbyname(server)
            socket.create_connection((host, 80), 2)
        except Exception:
            logger.warning("Internet does not seem to be available")
            time.sleep(3)
            count +=1
        else:
            logger.debug("Internet connection working")
            return True


