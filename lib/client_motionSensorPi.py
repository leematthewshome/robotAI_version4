#!/usr/bin/env python
"""
===============================================================================================
Sensor for detecting motion using Open CV
Author: Lee Matthews 2020
Open computer vision (Open CV) libraries required 
===============================================================================================
"""
from datetime import datetime
from datetime import timedelta
import imutils
import time
import cv2
import pika
import logging
import base64
import os
import io

#imports for using Pi Camera
import picamera
from picamera.array import PiRGBArray
"""
from picamera.array import PiRGBArray
from picamera import PiCamera
from picamera import PiCameraCircularIO
from picamera import PiVideoFrameType
"""
#settings for image capture and processing
resolution = [640, 480]
minArea = 5000
deltaThresh = 5
vidSeconds = 30

avg_image = None                # to store ongoing comparison image
uploadEvery = 3                 # how often (seconds) to send image
videoFileSize = 4000000         # seems to equate to 60 second videos
recordTime = 35                 # how long record after motion
lastUploaded = datetime.now()   # to store last time image sent


class motionLoop(object):

    def __init__(self, ENVIRON):
        logging.basicConfig()
        self.logger = logging.getLogger(__name__)
        self.logger.level = logging.DEBUG
        #self.logger.level = logging.INFO
        print 
        # setup variables for motion detection process
        #-------------------------------------------------
        self.logger.debug("Setting motion detection delay...")
        if ENVIRON["secureMode"]:
            ENVIRON["motionDelay"] = 60
        else:
            ENVIRON["motionDelay"] = 60
        ENVIRON["motionTime"] = datetime.now() + timedelta(seconds=ENVIRON["motionDelay"])
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


    # Loop to detect motion using Pi camera
    #------------------------------------------------------------------------------------
    def detectPiCamera(self):   
        self.logger.debug("Starting to detect Motion")
        saveAt = None
        lastAlert = datetime.today()
        startDetecting = datetime.now() + timedelta(seconds=15)                     # avoid detection while setting average

        self.logger.debug("Warming up camera...")
        time.sleep(3)

        with picamera.PiCamera() as camera:
            camera.resolution = tuple(resolution) 
            #self.stream = picamera.PiCameraCircularIO(camera, seconds=30)          #seconds parameter not working
            self.stream = picamera.PiCameraCircularIO(camera, size=videoFileSize)
            camera.start_recording(self.stream, format='h264')
            try:
                while True:
                    # check for motion on a routine interval
                    time.sleep(.3)
                    frame, isMotion = self.detect_motion(camera)
                    # take action if motion detected
                    if isMotion and datetime.now() > startDetecting:
                        self.detectionEvent(camera, frame)
                        if saveAt is None:
                            saveAt = datetime.now() + timedelta(seconds=recordTime)
                    # check to see if we need to save video due to motion
                    if saveAt:
                        if saveAt < datetime.now():
                            self.write_video()
                            saveAt = None
            finally:
                camera.stop_recording()            
            
            
    # Detect whether motion is indicated between avg_image and current image
    #------------------------------------------------------------------------------------
    def detect_motion(self, camera):
        isMotion = False
        timestamp = datetime.now()
        global avg_image
        global lastUploaded
        global uploadEvery
        global deltaThresh

        rawCapture = PiRGBArray(camera, size=tuple(resolution))
        camera.capture(rawCapture, format="bgr", use_video_port=True)
        frame = rawCapture.array

        # resize the frame, convert it to grayscale, and blur it
        frame = imutils.resize(frame, width=500)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # if the average frame is None, initialize it
        if avg_image is None:
            avg_image = gray.copy().astype("float")
            rawCapture.truncate(0)
            return frame, False

        # accumulate weighted avg between the current frame and previous frames, then the difference b/w current frame and avg
        cv2.accumulateWeighted(gray, avg_image, 0.5)
        frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg_image))

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

        # check to see if we need to stop detecting of submit image to brain
        if (timestamp - lastUploaded).seconds >= uploadEvery:
            print("Checking for stop indicator and uploading image")
            lastUploaded = timestamp
        
        rawCapture.truncate(0)    
        return frame, isMotion
            

            
    # Write data from circular stream to file
    #------------------------------------------------------------------------------------
    def write_video(self):
        self.logger.debug('Writing circular video buffer to file...')
        filepath = os.path.join(self.ENVIRON["topdir"], 'static/motionImages', datetime.now().strftime("%Y%m%d%H%M%S") + '.h264') 

        with self.stream.lock:
            # Find the first header frame in the video
            for frame in self.stream.frames:
                if frame.frame_type == picamera.PiVideoFrameType.sps_header:
                    self.stream.seek(frame.position)
                    break
            # Write the rest of the stream to disk
            with io.open(filepath, 'wb') as output:
                output.write(self.stream.read())
        self.logger.debug('File ' + filepath + ' created!')
        # Wipe the circular stream once we're done
        self.stream.seek(0)
        self.stream.truncate()
        ###################################################################
        # TODO add code to synch video files to the cloud and delete locally
        ###################################################################
                

                
    # Work out what we need to do when motion detected
    #------------------------------------------------------------------------------------
    def detectionEvent(self, camera, frame):
        self.logger.debug('Motion detected. Determining course of action... ')

        # If we are already talking then no need to start speech again
        if self.ENVIRON["talking"]:
            self.logger.debug('Motion but talking...So sending image to recognize faces')
            self.sendImage(frame, 'motion')
            time.sleep(1)
        else:  
            # check for either security or friendly mode and delay has expired
            if (self.ENVIRON["secureMode"] or self.ENVIRON["friendMode"]) and (self.ENVIRON["motionTime"] < datetime.now()):
                self.logger.debug('Motion detected and timer has expired so taking action. ')
                # send image to brain to check if person detected
                self.sendImage(frame, 'motion')
            else:
                diff = self.ENVIRON["motionTime"] - datetime.now()
                self.logger.debug("Motion detected but taking no action. %s seconds delay remains" % str(diff.seconds))
                pass
                

        
    # Send image file to server
    #------------------------------------------------------------------------------------
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
    ENVIRON["topdir"] = '/home/pi/robotAI4/'


    doSensor(ENVIRON)
    
    