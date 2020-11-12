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
IS_PI_DEVICE = None #check to see if testing on Pi device
try:
    import RPi.GPIO as GPIO
    from hx711 import HX711
    IS_PI_DEVICE = True
except Exception as e:
    IS_PI_DEVICE = False
    import RPi_DUMMY.GPIO as GPIO
    from HX711_DUMMY.hx711 import HX711

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
import queries

#======GLOBAL VARIABLES==========
GPIO_TRIGGER = 23 #ultrasonic
GPIO_ECHO = 24    #ultrasonic
HX711_IN = 5       #weight sensor in
HX711_OUT = 6      #weight sensor out
UPLOAD_RATE = 3  #number of times collecting data before uploading to server
ERR_PATH = "/home/pi/ZBinData/errData.json"

if IS_PI_DEVICE:
    JSON_PATH = "/home/pi/ZBinData/binData.json"
    DB_PATH = "/home/pi/ZBinData/zotbin.db"
else:  #directories for testing
    JSON_PATH =  "./simulation/binData.json" #"../binData.json"
    DB_PATH = "../database/zotbin.db"

class ZotBins():
    def __init__(self,send_data=True,frequency_sec=300):
        """
        send_data<Bool>: determines whether or not the algortihm should
            send data to the tippers database or
            just save the data locally.
        frequency_sec<int>: determines the sampling rate of which the
            algorithm collects data
        """

        #extract the json info
        self.bin_info = self.parse_JSON()
        self.collect_weight, self.collect_distance = self.bin_info["collectWeight"], self.bin_info["collectDistance"]

        #====General GPIO Setup====================
        GPIO.setmode(GPIO.BCM) #for weight sensor

        #====set up Ultrasonic GPIO pins============
        GPIO.setup(GPIO_TRIGGER, GPIO.OUT) #for ultrasonic sensor
        GPIO.setup(GPIO_ECHO, GPIO.IN) #for ultrasonic sensor

        #=====setup hx711 GPIO pins=================
        if IS_PI_DEVICE:
            self.hx = HX711(HX711_IN, HX711_OUT)
            self.hx.set_reading_format("LSB", "MSB")
            self.hx.set_reference_unit(float( self.bin_info["weightCal"] ))
            self.hx.reset()
            self.hx.tare()

        #========Query Information======================================
        #assign variables
        self.bin_ID = self.bin_info["binID"]
        self.weight_sensor_ID = self.bin_ID
        self.weight_type = 2
        self.ultrasonic_sensor_ID = self.bin_ID + 'D'
        self.ultrasonic_type = 3
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        #========class variables for data collection algorithm=========
        #generic
        self.send_data=send_data
        self.sleep_rate=frequency_sec
        self.upload_rate = frequency_sec * UPLOAD_RATE

        #TODO: Add more info about Weight Scale set-up on the Documentation
        # I noticed that the serial port may alternate between /dev/ttyACM1 and /dev/ttyACM0. I also noticed that compile and upload the weight sensor code from the Arduino matters because it tell the code which Serial Port to output to. - okyang
        if IS_PI_DEVICE:
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

    def run(self,ult_collect=True,weight_collect=True,tippers_push=True,dist_sim=False,weight_sim=False):
        """
        This function runs the data collection algorithm
        ult_collect<bool>:       Parameter that specifies if the bin can ultrasense. Default set to true.
        weight_collect<bool>:    Parameter that specifies whether or not weight data should be collected.
        tippers_push<bool>:      Parameter that specifies whether or not local data should be pushed to Tippers.
        dist_sim<bool>:          Specifies whether to simulate distance data or use the physical ultrasonic sensor.
                                If True, it returns the default value: 60.0 (cm)
        weight_sim<bool>:        Specifies whether to simulate weight data or use the physical weight sensor for data.
                                If True, it returns the default value: 0.0 (cm)
        """
        #initialize ZState of bin
        with open(JSON_PATH) as main_data:
            sensor_IDs = eval(main_data.read())["bin"]
            self.state = ZBinErrorDev.ZState(sensor_IDs[1].keys())
        failure = "NULL" #contains error messages, default no errors
        #=======MAIN LOOP==========
        while True:
            try:
                #=========Measure the Weight===============================
                weight = self.measure_weight(weight_collect,weight_sim)

                #========Measure the Distance==============================
                distance = self.measure_dist(ult_collect,dist_sim)

                #=========Extract timestamp=================================
                timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

                #=========Write to Local===================================
                self.add_data_to_local(timestamp,weight,distance,failure)

                #========Sleep to Control Frequency of Data Aquisition=====
                time.sleep(self.sleep_rate)

                #=========Write to Tippers=================================
                self.update_tippers(self.weight_sensor_ID,self.weight_type,self.ultrasonic_sensor_ID, self.ultrasonic_type, self.headers, self.bin_info)

                #========Sensor Failure Checking=============
                failure = self.state.check()

                #========Send a notification============
                if failure != "NULL" and self.send_data and self.state.checkConnection():
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
                return 60.0
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
                return 30.0
            else:
                #set the Trigger to HIGH
                GPIO.output(GPIO_TRIGGER, True)

                #set the Trigger after 0.01 ms to LOW
                time.sleep(0.00001)
                GPIO.output(GPIO_TRIGGER, False)

                start_time = time.time()
                stop_time = time.time()

                try:
                    with self.time_limit(5):
                        while GPIO.input(GPIO_ECHO) == 0:
                            start_time = time.time()
                        while GPIO.input(GPIO_ECHO) == 1:
                            stop_time = time.time()
                except Timeout:
                    return "NULL" #we know it failed

                time_elapsed = stop_time - start_time
                distance = (time_elapsed*34300)/2
                return distance

    def parse_JSON(self):
        """
        This function parses the json file in the absolute path
        of '/home/pi/ZBinData/binData.json' and returns a dictionary
        """
        with open(JSON_PATH) as bindata:
        	bin_info = eval( bindata.read() )["bin"][0]
        return bin_info

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
        conn = sqlite3.connect(DB_PATH)
        
        conn.execute(queries.create_local_table)
        conn.commit()

        #creates a new error table to hold a list of error messages, the main table will contain the name of the error table
        err_table = failure

        conn.execute(queries.insert_data.format(timestamp,weight,distance,err_table))
        conn.commit()
        conn.close()

    def update_tippers(self,WEIGHT_SENSOR_ID, WEIGHT_TYPE,
    ULTRASONIC_SENSOR_ID, ULTRASONIC_TYPE, HEADERS, bin_info):
        """
        This function updates the tippers database with local data
        """
        
        if ( (time.time() - self.post_time > self.upload_rate) and self.send_data ):
            print("Updating tippers")
            d = list()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute(queries.select_data)
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
                print("Data to be pushed: \n", d)
                r = requests.post(bin_info["tippersurl"], data=json.dumps(d), headers=HEADERS)
                #after updating tippers delete from local database
                conn.execute(queries.delete_data)
                conn.commit()
                self.post_time = time.time()
                self.state.reset(str(WEIGHT_SENSOR_ID))
                self.state.reset(str(ULTRASONIC_SENSOR_ID))
                print("Tippers status code: ", r.status_code)
            except Exception as e:
                print("Tippers error: ", e)
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
        #NOTE: changed format of csv file to replace : with - since that doesn't work with windows
        self.log_file = "logs/zbinlog_{}.csv".format(start_time).replace(':','-')
        logging.basicConfig(filename=self.log_file, level=logging.WARNING, format='"%(asctime)s","%(message)s"')

class Timeout(Exception):
    """
    This is for the timed signal excpetion
    """
    pass

if __name__ == "__main__":
    zot = ZotBins(send_data=True, frequency_sec=300) #initialize the ZotBins object
    try:
        zot.run(ult_collect=zot.collect_distance,weight_collect=zot.collect_weight,dist_sim=True,weight_sim=True) #run the data collection algorithm
    finally:
        GPIO.cleanup()
        sys.exit()
