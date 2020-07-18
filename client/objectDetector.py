import cv2
import os
import numpy as np

#-------------------------------------------------------------------------------------------------------------------------
# Object Detection Detector
#-------------------------------------------------------------------------------------------------------------------------
class detectorAPI:

    def __init__(self):
        # filepath parameters parameters
        self.file_path = os.path.dirname(os.path.realpath(__file__))
        self.model_path = os.path.join(self.file_path, "MLModels/MobileNetSSD_deploy.caffemodel")
        self.proto_path = os.path.join(self.file_path, "MLModels/MobileNetSSD_deploy.prototxt.txt")
        self.conf_cutoff = 0.5

	# initialize the list of class labels for detection
        self.CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
		"dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]
        self.net = cv2.dnn.readNetFromCaffe(self.proto_path, self.model_path)


    def objectCount(self, imgbin):
        frame = cv2.imdecode(np.frombuffer(imgbin, np.uint8), -1)
        #frame = imutils.resize(frame, width=400)
        # grab the frame dimensions and convert it to a blob
        #(h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
        # pass the blob through the network and obtain the detections and predictions
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


