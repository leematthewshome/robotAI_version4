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
import pickle
import imutils

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

        # parameters for object detection model
        obj_model_path = os.path.join(ENVIRON["topdir"], "static/MLModels/object/MobileNetSSD_deploy.caffemodel")
        obj_proto_path = os.path.join(ENVIRON["topdir"], "static/MLModels/object/MobileNetSSD_deploy.prototxt.txt")
        self.CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
                "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]
        self.obj_net = cv2.dnn.readNetFromCaffe(obj_proto_path, obj_model_path)
        self.obj_conf_cutoff = 0.5

        # parameters for face identification model
        modelPath = os.path.join(ENVIRON["topdir"], "static/MLModels/faceid/res10_300x300_ssd_iter_140000.caffemodel")
        protoPath = os.path.join(ENVIRON["topdir"], "static/MLModels/faceid/deploy.prototxt")
        self.face_detector = cv2.dnn.readNetFromCaffe(protoPath, modelPath)
        self.face_embedder = cv2.dnn.readNetFromTorch(os.path.join(ENVIRON["topdir"], "static/MLModels/faceid/openface_nn4.small2.v1.t7"))
        self.face_recognizer = pickle.loads(open(os.path.join(ENVIRON["topdir"], "static/MLModels/faceid/output/recognizer.pickle"), "rb").read())
        self.face_labels = pickle.loads(open(os.path.join(ENVIRON["topdir"], "static/MLModels/faceid/output/le.pickle"), "rb").read())
        self.face_conf_cutoff = 0.5


    # function to detect objects. Returns a dictionary of objects by count
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
        return dictObjects


    # function to recognize faces. Returns a list of faces
    #-----------------------------------------------------------------------
    def recognizer(self, imgbin):
        faces = False
        listFaces = []
        image = cv2.imdecode(np.frombuffer(imgbin, np.uint8), -1)
        image = imutils.resize(image, width=600)
        (h, w) = image.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0), swapRB=False, crop=False)
        self.face_detector.setInput(blob)
        detections = self.face_detector.forward()
        # loop over the detections
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > self.face_conf_cutoff:
                faces = True
                self.logger.debug('Found a face. Will try to recognise')
                # compute the (x, y) coordinates of the face and extract that image as 'face'
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                face = image[startY:endY, startX:endX]
                (fH, fW) = face.shape[:2]
                # ensure the face width and height are sufficiently large
                if fW < 20 or fH < 20:
                    self.logger.debug('Face is not big enough to analyse')
                    continue
                # construct a blob for the face ROI, then pass the blob through our face model to quantify the face
                faceBlob = cv2.dnn.blobFromImage(face, 1.0 / 255, (96, 96), (0, 0, 0), swapRB=True, crop=False)
                self.face_embedder.setInput(faceBlob)
                vec = self.face_embedder.forward()
                # perform classification to recognize the face
                preds = self.face_recognizer.predict_proba(vec)[0]
                j = np.argmax(preds)
                proba = preds[j]
                name = self.face_labels.classes_[j]
                # what was the result
                listFaces.append(name)
        if not faces:
            self.logger.debug('No faces were detected in the image')
            
        return listFaces
        

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

            # use ML to detect objects in the image
            # -----------------------------------------------------------------
            self.logger.debug('Analysing the image for recognized objects')
            detected = self.objectCount(imgbin)
            
            # use ML to recognise faces in the image, add to previous results
            # -----------------------------------------------------------------
            self.logger.debug('Analysing the image for recognized faces')
            faces = self.recognizer(imgbin)
            detected["faces"] = faces

            # respond to the client device that submitted the message
            body = json.dumps(detected)
            self.logger.debug('Sending data to: ' + reply_to + '. body = ' + body)
            channel1 = msgQueue.channel()
            channel1.queue_declare(reply_to)
            properties = pika.BasicProperties(app_id='motion', content_type='application/json', reply_to='Central')
            channel1.basic_publish(exchange='', routing_key=reply_to, body=body, properties=properties)


