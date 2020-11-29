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

#imports for using Pi Camera
from picamera.array import PiRGBArray
from picamera import PiCamera

#settings for image capture and processing
resolution = [640, 480]
frameRate = 15
minArea = 5000
uploadEvery = 3 #seconds
deltaThresh = 5
vidSeconds = 5


class motionLoop(object):

    def __init__(self, ENVIRON):
        logging.basicConfig()
        self.logger = logging.getLogger(__name__)
        self.logger.level = logging.DEBUG
        #self.logger.level = logging.INFO
        
        # setup variables for motion detection process
        #-------------------------------------------------
        self.logger.debug("Setting motion detection delay...")
        if ENVIRON["secureMode"]:
            ENVIRON["motionDelay"] = 60
        else:
            ENVIRON["motionDelay"] = 60
        ENVIRON["motionTime"] = datetime.datetime.now() + datetime.timedelta(seconds=ENVIRON["motionDelay"])
        self.logger.debug("Motion detection delay set to " + str(ENVIRON["motionDelay"]))

        self.ENVIRON = ENVIRON
        credentials = pika.PlainCredentials(self.ENVIRON["queueUser"], self.ENVIRON["queuePass"])
        self.parameters = pika.ConnectionParameters(self.ENVIRON["queueSrvr"], self.ENVIRON["queuePort"], '/',  credentials)


    # Loop to keep checking every 5 seconds whether we should turn motion detection on
    #------------------------------------------------------------------------------------
    def runLoop(self):
        self.logger.debug("Starting Motion Sensor Loop")
        while True:
            if self.ENVIRON["motion"]:
                self.detectPiCamera()
            else:
                time.sleep(5)


    # Loop to detect motion using the camera
    #------------------------------------------------------------------------------------
    def detectPiCamera(self):
        self.logger.debug("Starting to detect Motion")

        camera = PiCamera()
        camera.resolution = tuple(resolution) 
        camera.framerate = frameRate
        rawCapture = PiRGBArray(camera, size=tuple(resolution))
        self.logger.debug("Warming up camera...")
        time.sleep(3)
        avg = None
        lastUploaded = datetime.datetime.now()

        lastAlert = datetime.datetime.today()
        frames = 0
        
        # capture frames from the camera
        for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
            # grab the raw NumPy array representing the image and initialize the timestamp
            frame = f.array
            timestamp = datetime.datetime.now()
            isMotion = False

            # resize the frame, convert it to grayscale, and blur it
            frame = imutils.resize(frame, width=500)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            # if the average frame is None, initialize it
            if avg is None:
                avg = gray.copy().astype("float")
                rawCapture.truncate(0)
                continue

            # accumulate weighted avg between the current frame and previous frames, then the difference b/w current frame and avg
            cv2.accumulateWeighted(gray, avg, 0.5)
            frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

            # threshold the delta image, dilate the thresholded image to fill in holes, then find contours on thresholded image
            thresh = cv2.threshold(frameDelta, deltaThresh, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = imutils.grab_contours(cnts)
            
            # loop over the contours, but ignore small differences
            for c in cnts:
                if cv2.contourArea(c) < minArea:  
                    continue
                isMotion = True
                
            # if motion was detected or upload time has expired
            if isMotion or (timestamp - lastUploaded).seconds >= uploadEvery:
                ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
                cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
                
                #if motion detected check if we should take action
                if isMotion:
                    self.detectionEvent(camera, frame)
                
                #if timeout then send image and check if we should exit
                if (timestamp - lastUploaded).seconds >= uploadEvery:
                    self.logger.debug("Checking for stop indicator and uploading image")
                    lastUploaded = timestamp
                    self.sendImage(frame, 'camera')
                    if self.ENVIRON["motion"] == False:
                        self.logger.debug("Time to stop detecting motion")
                        camera.clear()
                        break

            rawCapture.truncate(0)




    # Work out what we need to do when motion detected
    # ============================================================================================
    def detectionEvent(self, camera, frame):
        self.logger.debug('Motion detected. Determining course of action... ')

        # If we are already talking then no need to start speech again
        if self.ENVIRON["talking"]:
            self.logger.debug('Motion detected but already talking.... ')
            # TODO add code to later try to identify who we might be talking to
            ###################################################################
        else:  
            # check for either security or friendly mode and delay has expired
            if (self.ENVIRON["secureMode"] or self.ENVIRON["friendMode"]) and (self.ENVIRON["motionTime"] < datetime.datetime.now()):
                self.logger.debug('Motion detected and timer has expired so taking action. ')
                # send image to brain to check if person detected
                self.sendImage(frame, 'motion')
                # record X seconds of video and synch to cloud anyway
                filepath = os.path.join('/home/pi/robotAI4/static/motionImages/', datetime.datetime.now().strftime("%Y%m%d%H%M%S") + '.h264') 
                camera.start_recording(filepath)
                time.sleep(vidSeconds)
                camera.stop_recording()
                # TODO add code to synch video files to the cloud and delete locally
                ###################################################################
            else:
                diff = self.ENVIRON["motionTime"] - datetime.datetime.now()
                self.logger.debug("Motion detected but taking no action. %s seconds delay remains" % str(diff.seconds))
                pass
                

        
    # Send image file to server
    # ============================================================================================
    def sendImage(self, frame, requestType):
        retval, buffer = cv2.imencode('.jpg', frame)
        jpgb64 = base64.b64encode(buffer)
        properties = pika.BasicProperties(app_id=requestType, content_type='image/jpg', reply_to=self.ENVIRON["clientName"])
        try:
            connection = pika.BlockingConnection(self.parameters)
            channel = connection.channel()
            channel.basic_publish(exchange='', routing_key='Central', body=jpgb64, properties=properties)
            connection.close()
        except:
            self.logger.error('Unable to send image to Message Queue ' + self.ENVIRON["queueSrvr"])
        

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
    queueSrvr = '192.168.1.200'
    queuePort = 5672
    queueUser = 'guest'
    queuePass = 'guest'
    connectMsg = body='{"type":"connection", "name":"' + clientName + '"}'
    motionSensor = True

    ENVIRON = {}
    ENVIRON["clientName"] = clientName                                      #the name of our client device, eg. FrontDoor
    ENVIRON["motion"] = True                                                #flags whether to run motion sensor
    ENVIRON["queueSrvr"] = queueSrvr
    ENVIRON["queuePort"] = queuePort
    ENVIRON["queueUser"] = queueUser
    ENVIRON["queuePass"] = queuePass
    ENVIRON["secureMode"] = True
    ENVIRON["friendMode"] = True
    ENVIRON["talking"] = False


    doSensor(ENVIRON)
    
    doSensor(ENVIRON, SENSORQ, MIC)


