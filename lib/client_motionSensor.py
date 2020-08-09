#!/usr/bin/env python
"""
===============================================================================================
Sensor for detecting motion using Open CV
Author: Lee Matthews 2020
Open computer vision (Open CV) libraries required 
===============================================================================================
"""
import datetime
import imutils
import time
import cv2
import pika
import logging
import base64
import os


class motionLoop(object):

    def __init__(self, ENVIRON):
        logging.basicConfig()
        self.logger = logging.getLogger(__name__)
        #self.logger.level = logging.DEBUG
        self.logger.level = logging.INFO
        self.ENVIRON = ENVIRON
        credentials = pika.PlainCredentials(self.ENVIRON["queueUser"], self.ENVIRON["queuePass"])
        self.parameters = pika.ConnectionParameters(self.ENVIRON["queueSrvr"], self.ENVIRON["queuePort"], '/',  credentials)

        # setup variables for motion detection process
        #-------------------------------------------------
        self.framesCheck = 10                           
        self.chatDelay = 0
        self.delay = 10
        self.min_area = 500
        self.detectPin = 0


    # Loop to keep checking every 5 seconds whether we should turn motion detection on
    #------------------------------------------------------------------------------------
    def runLoop(self):
        self.logger.debug("Starting Motion Sensor Loop")
        while True:
            if self.ENVIRON["motion"]:
                self.detectCamera()
            else:
                time.sleep(5)
           
            
    # Loop to detect motion using the camera
    #------------------------------------------------------------------------------------
    def detectCamera(self):
        self.logger.debug("Starting to detect Motion")
        # define feed from camera
        camera = cv2.VideoCapture(0)
        time.sleep(1)
        # initialize variables used by the motion sensing
        firstFrame = None
        lastAlert = datetime.datetime.today()
        frames = 0
        
        # loop over the frames of the video feed and detect motion
        while True:
                
            # grab the current frame 
            (grabbed, frame) = camera.read()
            frames += 1

            # resize the frame, convert it to grayscale, and blur it
            frame = imutils.resize(frame, width=500)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            # if the first frame is None, initialize it
            if firstFrame is None:
                firstFrame = gray
                continue

            # compute the absolute difference between the current frame and first frame
            frameDelta = cv2.absdiff(firstFrame, gray)
            thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]
            # Update the reference frame
            firstFrame = gray
            # dilate the thresholded image to fill in holes, then find contours on thresholded image
            thresh = cv2.dilate(thresh, None, iterations=2)
            #open CV seems to change the number of params returned
            try:
                (img, cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            except:
                (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # loop over the contours
            for c in cnts:
                # if the contour is too small, ignore it
                if cv2.contourArea(c) < self.min_area:
                    continue
                #motion must be detected, see if we need to trigger a new Alert for the motion
                lastAlert = self.detectionEvent(lastAlert, camera, frame)

            # check the ENVIRON setting when frame count reaches check point
            if frames > self.framesCheck:
                self.logger.debug("Checking to see if we should stop detecting motion")
                frames = 0
                if self.ENVIRON["motion"] == False:
                    self.logger.debug("Time to stop detecting motion")
                    # cleanup the camera quit function
                    camera.release()
                    break


    # Work out what we need to do when motion detected
    # ============================================================================================
    def detectionEvent(self, lastAlert, camera, frame):
        # Check lastAlert to see if we need to trigger a new Alert for the motion
        curDTime = datetime.datetime.today()
        self.logger.debug("Motion detected at %s " % curDTime)
        diff = curDTime - lastAlert
        
        # Only take action if the delay set between actions has expired
        if (diff.seconds) < self.delay:
            self.logger.debug("Motion delay has not expired. %s seconds remaining." % str(self.delay - diff.seconds)  )             
        else:
            lastAlert = curDTime
            self.logger.info("Motion detected at %s and motion delay has expired" % curDTime)
            
            # Send a message to the brain over the Message Queue
            if self.ENVIRON["SecureMode"] or self.ENVIRON["Identify"]:
                retval, image = camera.read()
                retval, buffer = cv2.imencode('.jpg', image)
                jpgb64 = base64.b64encode(buffer)
                properties = pika.BasicProperties(app_id='motion', content_type='image/jpg', reply_to=self.ENVIRON["clientName"])
                lastAlert = datetime.datetime.today()
                try:
                    before = datetime.datetime.today()
                    connection = pika.BlockingConnection(self.parameters)
                    channel = connection.channel()
                    channel.basic_publish(exchange='', routing_key='Central', body=jpgb64, properties=properties)
                    connection.close()
                    after = datetime.datetime.today()
                    self.logger.info("Time taken: " + str(after-before))                 
                except:
                    self.logger.error('Unable to send image to Message Queue ' + self.ENVIRON["queueSrvr"])

        return lastAlert

#---------------------------------------------------------------------------
# Function called by main robotAI procedure to start this sensor
#---------------------------------------------------------------------------
def doSensor(ENVIRON):
    loop = motionLoop(ENVIRON)
    loop.runLoop()


    
# **************************************************************************
# This will only be executed when we run the sensor on its own for debugging
# **************************************************************************
if __name__ == "__main__":
    print("******** WARNING ********** Starting Sensor from __main__ procedure")
    # need code here to setup default variables
    clientName = 'ClientDefault'
    queueSrvr = '192.168.0.50'
    queuePort = 5672
    queueUser = 'guest'
    queuePass = 'guest'
    connectMsg = body='{"type":"connection", "name":"' + clientName + '"}'
    motionSensor = True

    ENVIRON = {}
    ENVIRON["clientName"] = clientName                                      #the name assigned to our client device, eg. FrontDoor
    ENVIRON["motion"] = True                                                #flags whether to run motion sensor
    ENVIRON["queueSrvr"] = queueSrvr
    ENVIRON["queuePort"] = queuePort
    ENVIRON["queueUser"] = queueUser
    ENVIRON["queuePass"] = queuePass


    doSensor(ENVIRON)
    
    doSensor(ENVIRON, SENSORQ, MIC)

