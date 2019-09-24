"""
Authors: Owen Yang, David Pham, and Danny Tran
Notes:
- This is meant to be run with Python 3.5+
Resources:
- Some of the code here was used from other projects/tutorials
- ultrasonic resource: https://tutorials-raspberrypi.com/raspberry-pi-ultrasonic-sensor-hc-sr04/
- load ceel resources:
"""
#====timestamps imports=========
import time
import datetime

#====GPIO related imports====
import RPi.GPIO as GPIO
from hx711 import HX711

#=====API imports===============
import json
import requests

#======other imports=============
import sys
import sqlite3

#======GLOBAL VARIABLES==========
GPIO_TRIGGER = 23 #ultrasonic
GPIO_ECHO = 24    #ultrasonic

HX711IN = 5		  #weight sensor in
HX711OUT = 6	  #weight sensor out


class ZotBins():
    def __init__(self,sendData=True,frequencySec=600):
        #========class variables for data collection algorithm=========
        self.sendData=sendData
        self.frequencySec=frequencySec

        #====set up GPIO pins============
        GPIO.setmode(GPIO.BCM) #for weight sensor
        GPIO.setup(GPIO_TRIGGER, GPIO.OUT) #for ultrasonic sensor
        GPIO.setup(GPIO_ECHO, GPIO.IN) #for ultrasonic sensor


    def run(self):
        """
        Runs the data collection algorithm
        """

        #========Measure the Distance=========
        x = measure_dist()
        print(x)


    def measure_dist():
        """
        This function uses the ultrasonic sensor to measure the distance.
        TRIG - should be connected to pin 23
        ECHO - should be connected to pin 24
        Vcc  - should be connected to 5V pin
        GND  - should be connected to a GND pin (straight-foward)
        """
        # set Trigger to HIGH
        GPIO.output(GPIO_TRIGGER, True)

        # set Trigger after 0.01ms to LOW
        time.sleep(0.00001)
        GPIO.output(GPIO_TRIGGER, False)

        StartTime = time.time()
        StopTime = time.time()

        # save StartTime
        while GPIO.input(GPIO_ECHO) == 0:
            StartTime = time.time()

        # save time of arrival
        while GPIO.input(GPIO_ECHO) == 1:
            StopTime = time.time()

        # time difference between start and arrival
        TimeElapsed = StopTime - StartTime
        # multiply with the sonic speed (34300 cm/s)
        # and divide by 2, because there and back
        distance = (TimeElapsed * 34300) / 2

        return distance


    def parseJSON():
        """
        This function parses the json file in the absolute path
        of '/home/pi/ZBinData/binData.json' and returns a list
        """
        pass


if __name__ == "__main__":
    zot = ZotBins(sendData=True,frequencySec=600) #initialize the ZotBins object
    zot.run() #run the data collection algorithm
