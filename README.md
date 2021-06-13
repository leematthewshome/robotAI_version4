# robotAI_version4
This is the latest version of my AI / Automation platform. Designed this time to allow for distributed computing, via a central message queue and 'brain' to handle heavy computing requirements like machine learning and computer vision. The series of videos at the following link discusses the architecture and how to install: https://www.youtube.com/watch?v=vhBliXm4O28&list=PLuXBZmwbLVYLWkmod24M9E2TRY0Jn-gsN

Installation for both Client & Brain Devices
--------------------------------------------
sudo apt install python3-pip

sudo pip3 install imutils

sudo pip3 install numpy

sudo pip3 install pika

sudo apt update

sudo apt install libopencv-dev python3-opencv

Download and unzip the code from this site. Rename the folder to robotAI4


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
sudo apt update 

sudo pip3 install --upgrade tensorflow

sudo pip3 install -U scikit-learn

sudo pip3 install flask


Setup RabbitMQ via docker on Server / Brain
-------------------------------------------
this install is covered in video here: https://www.youtube.com/watch?v=Iwi7KrAoKFg

sudo apt install docker.io

systemctl start docker

systemctl enable docker

verify docker status with the following command: systemctl status docker

sudo groupadd docker

sudo usermod -aG docker $USER

Before we download and run the RabbitMQ docker container we will need to assign it a separate IP that will not be used by other computers on the network...

install ifconfig with the following command: sudo apt install -y net-tools

run the following command: config

look for the line where it lists your current network IP, for example:

    wlo1: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
    inet 192.168.1.105  netmask 255.255.255.0  broadcast 192.168.1.255"
    
as you can see from the above example my wireless network card is identified as "wlo1". so that we can map a separate external IP to the message queue we need to assign an extra IP to our network card. Choose one that will not be assigned to another device on your network.For example:

sudo ip addr add 192.168.1.200 dev wlo1

now install the rabbitmq docker container and run it

docker run -d -p 192.168.1.200:8080:15672 -p 192.168.1.200:5672:5672 --name robotai-queue rabbitmq:3-management


Finally...
----------------------------------------------
Update the settings.ini to reflect the chosen IP address and login credentials (guest:guest is default) for rabbitmq 

Ensure the message queue is running on your chosen IP address

Start the Brain code with the following command

    python3 robotAI_brain.py
    
Start the Client code on a separate device (or in separate script window) with the following command

    python3 robotAI_client.py

You should see the details of the client connecting to the brain via the message queue in the comments in each script window


