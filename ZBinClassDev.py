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

#=====logging import===========
import logging
from pathlib import Path

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
        """
        sendData<Bool>: determines whether or not the algortihm should
            send data to the tippers database or
            just save the data locally.
        frequencySec<int>: determines the sampling rate of which the
            algorithm collects data
        """
        #extract the json info
        self.bininfo = self.parseJSON()

        #====General GPIO Setup====================
        GPIO.setmode(GPIO.BCM) #for weight sensor

        #====set up Ultrasonic GPIO pins============
        GPIO.setup(GPIO_TRIGGER, GPIO.OUT) #for ultrasonic sensor
        GPIO.setup(GPIO_ECHO, GPIO.IN) #for ultrasonic sensor

        #=====setup hx711 GPIO pins=================
        self.hx = HX711(HX711IN, HX711OUT)
        self.hx.set_reading_format("LSB", "MSB")
        self.hx.set_reference_unit(float( self.bininfo["weightCal"] ))
        self.hx.reset()
        self.hx.tare()

        #========Query Information======================================
        #assign variables
        self.binID = self.bininfo["binID"]
        self.weightSensorID = self.binID
        self.weightType = 2
        self.ultrasonicSensorID = self.binID + 'D'
        self.ultrasonicType = 3
        self.headers = {
        	"Content-Type": "application/json",
        	"Accept": "application/json"
        }

        #========class variables for data collection algorithm=========
        #generic
        self.sendData=sendData
        self.frequencySec=frequencySec

        #time
        self.post_time=time.time()

        #========Setup Logging for errors===============================
        self.log_setup()

    def run(self,ultCollect=True,weightCollect=True,tippersPush=True,distSim=False,weightSim=False):
        """
        This function runs the data collection algorithm
        ultCollect<bool>:       Parameter that specifies if the bin can ultrasense. Default set to true.
        weightCollect<bool>:    Parameter that specifies whether or not weight data should be collected.
        tippersPush<bool>:      Parameter that specifies whether or not local data should be pushed to Tippers.
        distSim<bool>:          Specifies whether to simulate distance data or use the physical ultrasonic sensor.
                                If True, it returns the default value: 60.0 (cm)
        weightSim<bool>:        Specifies whether to simulate weight data or use the physical weight sensor for data.
                                If True, it returns the default value: 0.0 (cm)
        """
        #=======MAIN LOOP==========
        while True:
            try:
                #=========Measure the Weight===============================
                weight = self.measure_weight(weightCollect,weightSim)

                #========Measure the Distance==============================
                distance = self.measure_dist(ultCollect,distSim)

                #=========Extract timestamp=================================
                timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

                #=========Write to Local===================================
                self.add_data_to_local(timestamp,weight,distance)

                #========Sleep to Control Frequency of Data Aquisition=====
                time.sleep(self.frequencySec)

                #=========Write to Tippers=================================
                self.update_tippers(self,self.weightSensorID,self.weightType,self.ultrasonicSensorID, self.ultrasonicType, self.headers, self.bininfo)

            except Exception as e:
                self.catch(e)

    def measure_weight(self,collect=True,simulate=False):
        """
        This function measures the weight, if collect is True. It measures the weights 11 times,
        sorts it, and returns the median.

        collect<bool>
        simulate<bool>
        """
        if collect:
            if simulate:
                return 0.0
            else:
                #array to collect the weight measurements
                derek = []

                #collect a list of weight measurements
                for i in range(11):
                    derek.append(self.hx.get_weight(5))
                    self.hx.power_down()
                    self.hx.power_up()
                    time.sleep(0.25)

                return sorted(derek)[5]
        return "NULL"

    def measure_dist(self,collect=True,simulate=False):
        """
        This function uses the ultrasonic sensor to measure the distance.
        TRIG - should be connected to pin 23
        ECHO - should be connected to pin 24
        Vcc  - should be connected to 5V pin
        GND  - should be connected to a GND pin (straight-foward)

        If there is no ultrasonic sensor connected. You may use set the
        parameter 'simulate' to True in order to generate a value to return
        without using the ultrasonic sensor

        collect<bool>
        simulate<bool>
        """
        distance = "NULL"
        if collect:
            if simulate:
                return 60.0
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

    def null_check_convert(self,value):
    	"""
        [CURRENTLY UNUSED FUNCTION]
    	This function checks whether or not the given value is
    	the string "NULL" and converts it to a float if necessary.
    	value: a float or a string "NULL" that represents weight or distance data.
    	"""
    	if value == "NULL":
    		return 0.0
    	else:
    		assert(type(value)==float)
    		return value

    def add_data_to_local(self,timestamp, weight, distance):
    	"""
    	This function adds timestamp, weight, and distance data
    	to the SQLite data base located in "/home/pi/ZBinData/zotbin.db"
    	timestamp<str>: in the format '%Y-%m-%d %H:%M:%S'
    	weight<float>: float that represents weight in grams
    	distance<float>: float that represents distance in cm
    	"""
    	conn = sqlite3.connect("/home/pi/ZBinData/zotbin.db")
    	conn.execute('''CREATE TABLE IF NOT EXISTS "BINS" (
    		"TIMESTAMP"	TEXT NOT NULL,
    		"WEIGHT"	REAL,
    		"DISTANCE"	REAL
    	);
    	''')
    	conn.execute("INSERT INTO BINS (TIMESTAMP,WEIGHT,DISTANCE)\nVALUES ('{}',{},{})".format(timestamp,weight,distance))
    	conn.commit()
    	conn.close()

    def update_tippers(self,WEIGHT_SENSOR_ID, WEIGHT_TYPE,
    ULTRASONIC_SENSOR_ID, ULTRASONIC_TYPE, HEADERS, BININFO):
        """
        This function updates the
        """
        if ( (time.time() - self.post_time > self.frequencySec) and self.sendData ):
            d = list()
            conn = sqlite3.connect("/home/pi/ZBinData/zotbin.db")
        	cursor = conn.execute("SELECT TIMESTAMP, WEIGHT, DISTANCE from BINS")
            for row in cursor:
                timestamp,weight,distance = row
        		try:
        			#weight sensor data
        			if weight != "NULL":
        				d.append( {"timestamp": timestamp, "payload": {"weight": weight},
                                   "sensor_id" : WEIGHT_SENSOR_ID,"type": WEIGHT_TYPE})
        			#ultrasonic sensor data
        			if distance != "NULL":
        				d.append({"timestamp": timestamp,"payload": {"distance": distance},
                        "sensor_id" : ULTRASONIC_SENSOR_ID,"type": ULTRASONIC_TYPE})
        		except Exception as e:
        			print ("Tippers probably disconnected: ", e)
        			return

            r = requests.post(BININFO["tippersurl"], data=json.dumps(d), headers=HEADERS)
        	if DISPLAY: print("query status: ", r.status_code, r.text)
        	#after updating tippers delete from local database
        	conn.execute("DELETE from BINS")
        	conn.commit()

            self.post_time = time.time()
        else:
            pass

    def catch(self,e):
        '''
        Called when an error is raised during the ZotBins run(). Will capture exception
        into a logging file.
        '''
        logging.exception(e)

    def log_setup(self):
        '''
        Set ups the path of where the error log should be saved and how it should be formatted.
        '''
        start_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
        #check to see if there is a directory for logging errors
        p = Path('logs')
        if not p.exists() or not p.is_dir():
            p.mkdir()
        #generate a log file with name with start of run
        self.log_file = "logs/zbinlog_{}.csv".format(start_time)
        logging.basicConfig(filename=self.log_file, level=logging.WARNING, format='"%(asctime)s","%(message)s"')


if __name__ == "__main__":
    zot = ZotBins(sendData=True,frequencySec=10) #initialize the ZotBins object
    try:
        zot.run(ultCollect=True,weightCollect=True,distSim=True,weightSim=True) #run the data collection algorithm
    finally:
        GPIO.cleanup()
        sys.exit()
