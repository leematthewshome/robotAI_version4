# robotAI_version4
This is the latest version of my AI / Automation platform. Designed this time to allow for distributed computing, via a central message queue and 'brain' to handle heavy computing requirements like machine learning and computer vision.

Installation for both Client & Brain Devices
--------------------------------------------
sudo pip3 install imutils

sudo pip3 install numpy

sudo pip3 install pika

sudo apt update

sudo apt install libopencv-dev python3-opencv


Installation Specific to Client
--------------------------------
sudo apt install libttspico0 libttspico-utils libttspico-data -y

sudo apt-get install python3-pyaudio sox portaudio19-dev

sudo pip3 install --upgrade google-cloud-speech

sudo pip3 install --upgrade protobuf

test recording of voice with arecord using the following command: arecord -d 5 -f S16_LE test.wav

test playing back the resulting recording with: aplay test.wav

sudo apt-get install sox

install swig 3.0.10 or above (refer Snowboy Github site)

sudo apt-get install libatlas-base-dev

Download Snowboy project from Github, unzip, change directory to snowboy-master/swig/Python3 and run "make" to compile _snowboydetect.so.  Copy that file to lib/snowboy folder where RobotAI code is located


Installation Specific to Server / Brain
---------------------------------------
sudo pip3 install PyMySQL
