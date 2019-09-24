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
    def __init__(self,sendData=True,frequencySec=600,sim=False):
        """
        sendData<Bool>: determines whether or not the algortihm should
            send data to the tippers database or
            just save the data locally.
        frequencySec<int>: determines the sampling rate of which the
            algorithm collects data
        sim<bool>: if there are no sensors, users may simulate getting data
            from the sensors by assigning this variable as True.
        """
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
        #=======Parse JSON=========
        bininfo = self.parseJSON()
        print(bininfo)

        #=======MAIN LOOP==========
        while True:

            #========Measure the Distance==============================
            x = self.measure_dist()
            print(x)

            #=========Measure the Weight===============================

            #=========Format the data==================================

            #=========Write to Local===================================

            #=========Write to Tippers=================================

            #========Sleep to Control Frequency of Data Aquisition=====
            time.sleep(self.frequencySec)

            #temporary for testing
            break

    def measure_dist(self,simulate=False):
        """
        This function uses the ultrasonic sensor to measure the distance.
        TRIG - should be connected to pin 23
        ECHO - should be connected to pin 24
        Vcc  - should be connected to 5V pin
        GND  - should be connected to a GND pin (straight-foward)

        If there is no ultrasonic sensor connected. You may use set the
        parameter 'simulate' to True in order to generate a value to return
        without using the ultrasonic sensor
        """
        if simulate:
            return 0.0
        else:
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

    def parseJSON(self):
        """
        This function parses the json file in the absolute path
        of '/home/pi/ZBinData/binData.json' and returns a dictionary
        """
        with open("/home/pi/ZBinData/binData.json") as bindata:
        	bininfo = eval( bindata.read() )["bin"][0]
        return bininfo

if __name__ == "__main__":
    zot = ZotBins(sendData=True,frequencySec=10,sim=False) #initialize the ZotBins object
    zot.run() #run the data collection algorithm
