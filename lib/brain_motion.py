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
# Object Detection detector
#-------------------------------------------------------------------------------------------------------------------------
class detectorAPI:

    def __init__(self, ENVIRON):
        debugOn = True

        # setup logging based on level
        logging.basicConfig()
        logger = logging.getLogger("brain_motion")
        if debugOn:
            logger.level = logging.DEBUG
        else:
            logger.level = logging.INFO
        self.logger = logger
        
        self.ENVIRON = ENVIRON

        # filepath parameters parameters
        obj_model_path = os.path.join(ENVIRON["topdir"], "static/MLModels/object/MobileNetSSD_deploy.caffemodel")
        obj_proto_path = os.path.join(ENVIRON["topdir"], "static/MLModels/object/MobileNetSSD_deploy.prototxt.txt")
        self.obj_conf_cutoff = 0.5

        # initialize the list of class labels for detection
        self.CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
                "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]
        self.obj_net = cv2.dnn.readNetFromCaffe(obj_proto_path, obj_model_path)


    # function to detect objects
    #-----------------------------------------------------------------------
    def objectCount(self, imgbin):
        frame = cv2.imdecode(np.frombuffer(imgbin, np.uint8), -1)
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
        # pass the blob through the network and obtain the detections and predictions
        self.obj_net.setInput(blob)
        self.logger.debug('Running the model for object detections')
        detections = self.obj_net.forward()

        # loop over the detections
        dictObjects = {}
        for i in np.arange(0, detections.shape[2]):
            # filter out weak detections by ensuring the `confidence` is greater than the minimum confidence
            confidence = detections[0, 0, i, 2]
            if confidence > self.obj_conf_cutoff:
                # extract the index of the class label from the `detections`
                idx = int(detections[0, 0, i, 1])
                className = self.CLASSES[idx]
                self.logger.debug(className + " detected")
                #check if there is already an entry in dictionary
                if className in dictObjects:
                    dictObjects[className] = dictObjects[className] + 1
                else:
                    dictObjects[className] = 1

        #return list of what we detected
        return dictObjects


    # Function called by robotAI_brain for this set of logic
    #-----------------------------------------------------------------------
    def doLogic(self, msgQueue, content, reply_to, body):
        # If we received an image then check it for objects
        if content == "image/jpg":
            self.logger.debug('Decode the content and save the file')
            imgbin = base64.b64decode(body)
	
            # Overwrite current image stored for client
            # -------------------------------------------
            filePath = os.path.join(self.ENVIRON['topdir'], 'static/motionImages', reply_to + '.jpg') 
            with open(filePath, 'wb') as f_output:
                f_output.write(imgbin)
		
            # Store image in history folder for client
            # ----------------------------------------       
            folder = os.path.join(self.ENVIRON['topdir'], 'static/motionImages/', reply_to) 
            if not os.path.exists(folder):
                os.makedirs(folder)
            filePath = os.path.join(folder, datetime.now().strftime("%Y%m%d%H%M%S") + '.jpg') 
            with open(filePath, 'wb') as f_output:
                f_output.write(imgbin)
            self.logger.debug("Saved image to " + filePath )

            # use Machine learning to determine if a person exists in the image
            # -----------------------------------------------------------------
            self.logger.debug('Analysing the image using detectorAPI class')
            result = self.objectCount(imgbin)
            # respond to the client device that submitted the message
            body = json.dumps(result)
            self.logger.debug('Sending data to: ' + reply_to + '. body = ' + body)
            channel1 = msgQueue.channel()
            channel1.queue_declare(reply_to)
            properties = pika.BasicProperties(app_id='motion', content_type='application/json', reply_to='Central')
            channel1.basic_publish(exchange='', routing_key=reply_to, body=body, properties=properties)


