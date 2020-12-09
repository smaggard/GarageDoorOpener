#!/bin/env python3

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import sys
import logging
import time
import json
import RPi.GPIO as gpio
import Adafruit_DHT

# State pins
# Pins for the garage door reed switches that show if it's open or closed.
garage_door_1_state_pin = 17
garage_door_2_state_pin = 27
gpio.setmode(gpio.BCM)
gpio.setwarnings(False)
gpio.setup(garage_door_1_state_pin, gpio.IN, pull_up_down=gpio.PUD_UP)
gpio.setup(garage_door_2_state_pin, gpio.IN, pull_up_down=gpio.PUD_UP)

# Relay pins
# Pins that are connected to the relays that send the trigger to open/close the doors.
garage_door_1_door_pin = 23
garage_door_2_door_pin = 24
gpio.setmode(gpio.BCM)
gpio.setup(garage_door_1_door_pin, gpio.OUT)
gpio.setup(garage_door_2_door_pin, gpio.OUT)
gpio.output(garage_door_1_door_pin, True)
gpio.output(garage_door_2_door_pin, True)

# IoT configuration
host = "<iot_host>"
rootCAPath = "<root_CA>"
certificatePath = "<public cert>"
privateKeyPath = "<private key>"
useWebsocket = False
clientId = "garagedoor"

# Configure logging
logger = logging.getLogger("AWSIoTPythonSDK.core")
logger = logging.basicConfig(
    filename='garage_cont.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

# Init AWSIoTMQTTClient
myAWSIoTMQTTClient = None
myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId)
myAWSIoTMQTTClient.configureEndpoint(host, 8883)
myAWSIoTMQTTClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTClient connection configuration
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

myAWSIoTMQTTClient.connect()

# Custom MQTT message callback
def customCallback(client, userdata, message):
    text = data = json.loads(message.payload)
    if text['door'] == "garage_door_1":
        toggle(garage_door_1_door_pin)
    if text['door'] == "garage_door_2":
        toggle(garage_door_2_door_pin)

# Define Toggles
def toggle(pin):
    gpio.output(pin, False)
    time.sleep(0.2)
    gpio.output(pin, True)

def get_status():
    gd1_status_binary = gpio.input(garage_door_1_state_pin)
    gd2_status_binary = gpio.input(garage_door_2_state_pin)
    if gd1_status_binary:
        gd1_status = 100
    else:
        gd1_status = 0
    if gd2_status_binary:
        gd2_status = 100
    else:
        gd2_status = 0
    return gd1_status, gd2_status

def send_status(prev_gd1_status, prev_gd2_status):
    gd1_status,gd2_status = get_status()
    # Update is status has changed.
    if gd1_status != prev_gd1_status:
        myAWSIoTMQTTClient.publish("garage_door_1_status", gd1_status, 1)
    if gd2_status != prev_gd2_status:
        myAWSIoTMQTTClient.publish("garage_door_2_status", gd2_status, 1)
    return prev_gd1_status, prev_gd2_status

# Connect and subscribe to AWS IoT
myAWSIoTMQTTClient.subscribe("garage_door_cmd", 1, customCallback)
time.sleep(2)

# Publish to the same topic in a loop forever
while True:
    prev_gd1_status, prev_gd2_status = get_status()
    time.sleep(20)
    send_status(prev_gd1_status, prev_gd2_status)