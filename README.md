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


Installation Specific to Server / Brain
---------------------------------------
sudo pip3 install PyMySQL
