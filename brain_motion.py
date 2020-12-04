#!/usr/bin/python3
"""
===============================================================================================
Functions used by robotai_brian to process images sent from the client
Author: Lee Matthews 2020
===============================================================================================
"""
import logging
import cv2
import os
import numpy as np
import json
import base64
import pika
from datetime import datetime

#-------------------------------------------------------------------------------------------------------------------------
# Object Detection Detector
#-------------------------------------------------------------------------------------------------------------------------
class detectorAPI:

    def __init__(self, logger, topDir):
        self.logger = logger
        # filepath parameters parameters
        self.model_path = os.path.join(topDir, "static/MLModels/object/MobileNetSSD_deploy.caffemodel")
        self.proto_path = os.path.join(topDir, "static/MLModels/object/MobileNetSSD_deploy.prototxt.txt")
        self.conf_cutoff = 0.5

        # initialize the list of class labels for detection
        self.CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
                "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]
        print("loading dnn")
        self.net = cv2.dnn.readNetFromCaffe(self.proto_path, self.model_path)


    def objectCount(self, imgbin):
        frame = cv2.imdecode(np.frombuffer(imgbin, np.uint8), -1)
        #frame = imutils.resize(frame, width=400)
        # grab the frame dimensions and convert it to a blob
        #(h, w) = frame.shape[:2]
        #print("converting to blob")
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
        # pass the blob through the network and obtain the detections and predictions
        #print("getting objects")
        self.net.setInput(blob)
        detections = self.net.forward()

        # loop over the detections
        dictObjects = {}
        for i in np.arange(0, detections.shape[2]):
            # filter out weak detections by ensuring the `confidence` is greater than the minimum confidence
            confidence = detections[0, 0, i, 2]
            if confidence > self.conf_cutoff:
                # extract the index of the class label from the `detections`
                idx = int(detections[0, 0, i, 1])
                className = self.CLASSES[idx]
                        #check if there is already an entry in dictionary
                if className in dictObjects:
                    dictObjects[className] = dictObjects[className] + 1
                else:
                    dictObjects[className] = 1

        #return list of what we detected
        return dictObjects


#---------------------------------------------------------------------------
# Function called by robotAI_brain for this set of logic
#---------------------------------------------------------------------------
def doLogic(ENVIRON, msgQueue, content, reply_to, body):

    debugOn = True

    # setup logging using the python logging library
    #-----------------------------------------------------
    logging.basicConfig()
    logger = logging.getLogger("brain_motion")
    if debugOn:
        logger.level = logging.DEBUG
    else:
        logger.level = logging.INFO

    # If we received an image then check it for objects
    if content == "image/jpg":
        logger.debug('Decode the content and save the file')
        imgbin = base64.b64decode(body)
        
        # Overwrite current image stored for client
        # -------------------------------------------
        filePath = os.path.join(ENVIRON['topdir'], 'static/motionImages', reply_to + '.jpg') 
        with open(filePath, 'wb') as f_output:
            f_output.write(imgbin)
        
        # Store image in history folder for client
        # ----------------------------------------       
        folder = os.path.join(ENVIRON['topdir'], 'static/motionImages/', reply_to) 
        if not os.path.exists(folder):
            os.makedirs(folder)
        filePath = os.path.join(folder, datetime.now().strftime("%Y%m%d%H%M%S") + '.jpg') 
        with open(filePath, 'wb') as f_output:
            f_output.write(imgbin)
        logger.debug("Saved image to " + filePath )

        # use Machine learning to determine if a person exists in the image
        # -----------------------------------------------------------------
        logger.debug('Analysing the image using detectorAPI class')
        dt = detectorAPI(logger, ENVIRON['topdir'])
        logger.debug('Instantiated detectorAPI class, running objectCount...')
        result = dt.objectCount(imgbin)
        # respond to the client device that submitted the message
        body = json.dumps(result)
        logger.debug('About to send data: ' + body)
        logger.debug('Sending data to: ' + reply_to)
        channel1 = msgQueue.channel()
        channel1.queue_declare(reply_to)
        properties = pika.BasicProperties(app_id='motion', content_type='application/json', reply_to='Central')
        channel1.basic_publish(exchange='', routing_key=reply_to, body=body, properties=properties)


