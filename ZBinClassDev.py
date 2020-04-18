"""
Authors: Owen Yang, David Pham, and Danny Tran
Notes:
- This is meant to be run with Python 3.5+
Resources:
- Some of the code here was used from other projects/tutorials
- ultrasonic resource: https://tutorials-raspberrypi.com/raspberry-pi-ultrasonic-sensor-hc-sr04/
"""
#====timestamps imports=========
import time
import datetime
import signal
from contextlib import contextmanager

#====GPIO related imports====
isPiDevice = None #check to see if testing on Pi device
try:
    import RPi.GPIO as GPIO
    from hx711 import HX711
    isPiDevice = True
except Exception as e:
    isPiDevice = False
    #add dummy RPi modules to run tests

#=====API imports===============
import json
import requests

#=====logging import===========
import logging
from pathlib import Path

#======other imports=============
import sys
import sqlite3
import ZBinErrorDev
import serial

#======GLOBAL VARIABLES==========
GPIO_TRIGGER = 23 #ultrasonic
GPIO_ECHO = 24    #ultrasonic
HX711IN = 5       #weight sensor in
HX711OUT = 6      #weight sensor out
UPLOAD_RATE = 3   #number of times collecting data before uploading to server
ERRPATH = "/home/pi/ZBinData/errData.json"

if isPiDevice:
    JSONPATH = "/home/pi/ZBinData/binData.json"
    DBPATH = "/home/pi/ZBinData/zotbin.db"
else:  #directories for testing
    JSONPATH =  "../binData2.json" #"../binData.json"
    DBPATH = "../database/zotbin.db"

class ZotBins():
    def __init__(self,sendData=True,frequencySec=300):
        """
        sendData<Bool>: determines whether or not the algortihm should
            send data to the tippers database or
            just save the data locally.
        frequencySec<int>: determines the sampling rate of which the
            algorithm collects data
        """
        #extract the json info
        self.bininfo = self.parseJSON()
        self.collectWeight, self.collectDistance = self.bininfo["collectWeight"], self.bininfo["collectDistance"]

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
        self.sleepRate=frequencySec
        self.uploadRate = frequencySec * UPLOAD_RATE

        #TODO: Add more info about Weight Scale set-up on the Documentation
        # I noticed that the serial port may alternate between /dev/ttyACM1 and /dev/ttyACM0. I also noticed that compile and upload the weight sensor code from the Arduino matters because it tell the code which Serial Port to output to. - okyang
        try:
            self.ser = serial.Serial('/dev/ttyACM0',9600)
        except Exception as e:
            print(repr(e))
            self.ser = False
        #time
        self.post_time=time.time()

        #========Setup for errors===============================.
        self.log_file = None #name of the log file, path changed in log_setup
        self.log_setup() #logging
        self.state = None #sensor data (default set to None, change when add sensorID's later)

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
        #initialize ZState of bin
        with open(JSONPATH) as maindata:
            sensorIDs = eval(maindata.read())["bin"]
            self.state = ZBinErrorDev.ZState(sensorIDs[1].keys())
        failure = "NULL" #contains error messages, default no errors
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
                self.add_data_to_local(timestamp,weight,distance,failure)

                #========Sleep to Control Frequency of Data Aquisition=====
                time.sleep(self.sleepRate)

                #=========Write to Tippers=================================
                self.update_tippers(self.weightSensorID,self.weightType,self.ultrasonicSensorID, self.ultrasonicType, self.headers, self.bininfo)

                #========Sensor Failure Checking=============
                failure = self.state.check()

                #========Send a notification============
                if failure != "NULL" and self.sendData and self.state.checkConnection():
                    self.state.notify(Path(self.log_file))
            except Exception as e:
                self.catch(e)

    def measure_weight(self,collect=True,simulate=False):
        """
        This function measures the weight, if collect is True. It measures the weights 11 times,
        sorts it, and returns the median.
        collect<bool>: If True, it will communicate with the hx711 chip to collect weight data.
        simulate<bool>: If True, it will just return 0.0
        """
        if collect:
            if simulate:
                return 0.0
            elif not self.ser:
                return "NULL"
            else:
                try:
                    with self.time_limit(5):
                        return float(str(self.ser.readline(),'utf-8').rstrip())
                except Timeout:
                    return "NULL"
                except Exception as e:
                    print(repr(e))
                    return "NULL"
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
        if collect:
            if simulate:
                return 60.0
            else:
                #set the Trigger to HIGH
                GPIO.output(GPIO_TRIGGER, True)

                #set the Trigger after 0.01 ms to LOW
                time.sleep(0.00001)
                GPIO.output(GPIO_TRIGGER, False)

                StartTime = time.time()
                StopTime = time.time()

                try:
                    with self.time_limit(5):
                        while GPIO.input(GPIO_ECHO) == 0:
                            StartTime = time.time()
                        while GPIO.input(GPIO_ECHO) == 1:
                            StopTime = time.time()
                except Timeout:
                    return "NULL" #we know it failed

                TimeElapsed = StopTime - StartTime
                distance = (TimeElapsed*34300)/2
                return distance

    def parseJSON(self):
        """
        This function parses the json file in the absolute path
        of '/home/pi/ZBinData/binData.json' and returns a dictionary
        """
        with open(JSONPATH) as bindata:
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

    def add_data_to_local(self,timestamp, weight, distance, failure="NULL"):
        """
        This function adds timestamp, weight, and distance data
        to the SQLite data base located in "/home/pi/ZBinData/zotbin.db"
        timestamp<str>: in the format '%Y-%m-%d %H:%M:%S'
        weight<float>: float that represents weight in grams
        distance<float>: float that represents distance in cm
        failure<str>: hold list of error messages, or is default null
        """
        conn = sqlite3.connect(DBPATH)

        conn.execute('''CREATE TABLE IF NOT EXISTS BINS ("TIMESTAMP" TEXT NOT NULL, "WEIGHT" REAL, "DISTANCE" REAL,"MESSAGES"  TEXT);''')
        conn.commit()

        #creates a new error table to hold a list of error messages, the main table will contain the name of the error table
        err_table = failure

        conn.execute("INSERT INTO BINS(TIMESTAMP,WEIGHT,DISTANCE,MESSAGES)\nVALUES('{}',{},{},'{}')".format(timestamp,weight,distance,err_table))
        conn.commit()
        conn.close()

    def update_tippers(self,WEIGHT_SENSOR_ID, WEIGHT_TYPE,
    ULTRASONIC_SENSOR_ID, ULTRASONIC_TYPE, HEADERS, BININFO):
        """
        This function updates the tippers database with local data
        """
        if ( (time.time() - self.post_time > self.uploadRate) and self.sendData ):
            d = list()
            conn = sqlite3.connect(DBPATH)
            cursor = conn.execute("SELECT TIMESTAMP, WEIGHT, DISTANCE from BINS")
            for row in cursor:
                timestamp,weight,distance = row
                #weight sensor data
                if weight != "NULL":
                    d.append( {"timestamp": timestamp, "payload": {"weight": weight},
                               "sensor_id" : WEIGHT_SENSOR_ID,"type": WEIGHT_TYPE})
                #ultrasonic sensor data
                if distance != "NULL":
                    d.append({"timestamp": timestamp,"payload": {"distance": distance},
                    "sensor_id" : ULTRASONIC_SENSOR_ID,"type": ULTRASONIC_TYPE})

            #for the request, we should try wrapping it in a try catch block
            #what are we trying to capture in the for loop? It looks like we're just appending
            #   data to be sent
            #How should we handle the null case? Server acceptable?
            try:
                r = requests.post(BININFO["tippersurl"], data=json.dumps(d), headers=HEADERS)
                #after updating tippers delete from local database
                conn.execute("DELETE from BINS")
                conn.commit()
                self.post_time = time.time()
                self.state.reset()
            except Exception as e:
                self.catch(e,"Tippers probably disconnected.")
                self.state.increment("tippers")
                return
        else:
            pass

    @contextmanager
    def time_limit(self,seconds):
        """
        This is for the timed signal to limit the amount of time it takes for
        a function to run.
        """
        def signal_handler(signum, frame):
            raise TimeoutException("Timed out!")
        signal.signal(signal.SIGALRM, self._handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)

    def _handler(self,sig,frame):
        """
        This is for the timed signal to limit the amount of time it takes for
        a function to run.
        """
        raise Timeout

    def catch(self,e,msg=""):
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

class Timeout(Exception):
    """
    This is for the timed signal excpetion
    """
    pass

if __name__ == "__main__":
    zot = ZotBins(sendData=True) #initialize the ZotBins object
    #print("Initializing")
    try:
        zot.run(ultCollect=zot.collectDistance,weightCollect=zot.collectWeight,distSim=False,weightSim=False) #run the data collection algorithm
    finally:
        GPIO.cleanup()
        sys.exit()
