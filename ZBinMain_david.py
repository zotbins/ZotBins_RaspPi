#This code is intended to be used with Python 2

#====timestamps imports=========
import time
import datetime
#====data collection imports====
import sys
import RPi.GPIO as GPIO
#=====API imports===============
import json
import requests
#======weight sensor imports=====
from hx711 import HX711
#======other imports=============
import sqlite3
from socket import *
import urllib

DISPLAY = True

def main(SEND_DATA=True, FREQUENCY_SECONDS = 600):
        """
        This is the main function that collects data for the
        Raspberry Pi. This function manages data collection
        by the Raspberry Pi, performs error checking, and
        sends data to the UCI TIPPERS SERVER.
        [SEND_DATA]: a bool that turns on/off sending data to tippers
        [FREQUENCY_SECONDS] = wait time between calculating measurements lower time for testing, 600 seconds for actual use;
        """
        #============json parsing file===================
        with open("/home/pi/ZBinData/binData.json") as bindata:
                BININFO = eval( bindata.read() )["bin"][0]
        BinID = BININFO["binID"]
        #setting GPIO Mode for weight sensor.
        GPIO.setmode(GPIO.BCM)

        #Global Filtering Variables. If a measured weight difference is
        MAX_WEIGHT_DIFF = 11.9712793734
        MAX_DIST_DIFF = 0.8

        #GPIO port numbers
        HX711IN = 5             #weight sensor in
        HX711OUT = 6    #weight sensor out
        TRIG = 23               #ultrasonic sensor in
        ECHO = 24               #ultrasonic sensor out

        #query information
        WEIGHT_SENSOR_ID = BinID
        WEIGHT_TYPE = 2
        ULTRASONIC_SENSOR_ID = BinID+"D"
        ULTRASONIC_TYPE = 3
        HEADERS = {
                "Content-Type": "application/json",
                "Accept": "application/json"
        }
        
        #warning flags and checks
        ut_ping = 0             #ultrasonic timeout keeper, increments once per ping attempt
        wt_ping = 0             #weight sensor timeout keeper, only increments on NULL read weights not inaccurate readings
        UT_MAX = 50
        WT_MAX = 100
        #ERR_REPORT = 0
        #check_time = time.time() #tracks the timeout
        upload_time = 0 #number of unsuccessful uploads to tippers
        ut_on = True
        wt_on = True
        connected = True #isConnected('localhost',5050)
        #err_state = (ut_on,wt_on,connection) #keeps track of the previous state of the pi to prevent error report spamming

        #========================ultrasonic set up================================
        GPIO.setup(TRIG,GPIO.OUT)
        GPIO.setup(ECHO,GPIO.IN)
        MAX_ULTRASONIC_PING = 100; #~1ms 
        #========================hx711 set up=====================================
        hx = HX711(HX711IN, HX711OUT)
        hx.set_reading_format("LSB", "MSB")
        hx.set_reference_unit(float( BININFO["weightCal"] ))
        hx.reset()
        hx.tare()

        #====================loop Variables==============================
        #local vairables for previous weight and distance
        distance, weight = 0.0,0.0
        #local variable for determining when to push data
        post_time = time.time()
        try:
                while True:
                        #============start weight measurement================
                        #collecting a list of measurements
                        derek = []
                        for i in range(11):
                                derek.append( hx.get_weight(5) )

                        #taking median of sorted values and finding the difference
                        temp_weight = sorted(derek)[5]
                        weight_diff = abs( temp_weight - null_check_convert(weight) )

                        if DISPLAY: update_log("\nThis is the measured weight: "+str(temp_weight))

                        #filtering logic that ignores new weight reading when
                        #the difference is less than a certain number
                        if weight_diff < MAX_WEIGHT_DIFF:
                                #the previous weight will now be the current weight
                                if DISPLAY: update_log("Weight Diff not enough: "+str(weight_diff))
                        else:
                                #let the new weight be the current weight
                                weight = float(temp_weight)

                        if temp_weight>=-10 and temp_weight<0: #rounding negative numbers close to zero to zero
                                weight = 0.0
                        elif temp_weight <= -10: #gets rid of inaccurate negative numbers
                                hx.power_down()
                                hx.power_up()
                                time.sleep(.5)
                                update_log("large negative numbers: "+str(weight)+" on "+datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S') )
                                weight = "NULL"
                                #continue #ERROR: Large Negative Numbers

                        #reset hx711 chip
                        hx.power_down()
                        hx.power_up()
                        #=============end of weight collection======================

                        #=============start of ultrasonic measurement===============
                        GPIO.output(TRIG, False)
                        
                        #sensor pinging stuck
                        pulse_ping = 0
                        timed_out = False

                        #allowing ultrsaonic sensor to settle
                        time.sleep(.5)
                        #ultrasonic logic
                        GPIO.output(TRIG, True)
                        time.sleep(0.00001)
                        GPIO.output(TRIG, False)

                        while GPIO.input(ECHO)==0 and ping <= MAX_ULTRASONIC_PING:
                                pulse_start = time.time()
                                #POSSIBLE ERROR: stuck in while loop
                                pulse_ping = pulse_ping+1
                        
                        if ping == MAX_ULTRASONIC_PING:
                                timed_out = True
                                
                        pulse_ping = 0

                        while GPIO.input(ECHO)==1 and ping < MAX_ULTRASONIC_PING:
                                pulse_end = time.time()
                                #POSSIBLE ERROR: stuck in while loop
                                pulse_ping = pulse_ping+1
                                
                        if ping == MAX_ULTRASONIC_PING or timed_out:
                                timed_out = True
                                pulse_duration = 0 #what value is pulse ping if it times out??
                                ut_ping = ut_ping+1
                        else:
                                pulse_duration = pulse_end - pulse_start

                        #collecting temporary distance and finding the difference between previous distance and current distance
                        temp_distance = float(pulse_duration * 17150)
                        distance_diff = abs( temp_distance - distance )
                        #logic for filtering out distance data.
                        if distance_diff < MAX_DIST_DIFF and distance_diff > 0:
                                pass
                        else:
                                distance = round(temp_distance, 2)
                        #=============end of ultrasonic measurement===============
                        #for DEBUGGING
                        if DISPLAY:
                                update_log("Weight: "+str(weight))
                                update_log("Distance: "+str(distance)+" cm")
                                update_log("Time difference: "+str(time.time()-post_time))

                        #=======time stall========
                        time.sleep(120)

                        #===================post data locally=====================
                        timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
                        add_data_to_local(timestamp, weight, distance)
                        if DISPLAY: update_log("data added successfully to sqlite")
                        #====================post data to Tippers==================
                        #check if it is time to post
                        if (time.time() - post_time > FREQUENCY_SECONDS) and SEND_DATA:
                                #update tippers with all the data from local database
                                update_tippers(WEIGHT_SENSOR_ID, WEIGHT_TYPE, ULTRASONIC_SENSOR_ID, ULTRASONIC_TYPE, HEADERS, BININFO)
                                post_time = time.time() #reset post_time
                        else:
                                continue #Not time to Update TIPPERS yet
                        fail_check()

        except KeyboardInterrupt:
            if DISPLAY: update_log("Cleaning...")
            GPIO.cleanup()
            if DISPLAY: update_log("Bye!")
            sys.exit()

def null_check_convert(value):
        """
        This function checks whether or not the given value is
        the string "NULL" and converts it to a float if necessary.
        [value]: a float or a string "NULL" that represents weight or distance data.
        """
        if value == "NULL":
                wt_ping = wt_ping + 1
                return 0.0
        else:
                assert(type(value)== float)
                return value

def add_data_to_local(timestamp, weight, distance):
        """
        This function adds timestamp, weight, and distance data
        to the SQLite data base located in "/home/pi/ZBinData/zotbin.db"
        [timestamp]: str
        [weight]: float that represents weight in grams
        [distance]: float that represents distance in cm
        """

        conn = sqlite3.connect("/home/pi/ZBinData/zotbin.db")
        conn.execute('''CREATE TABLE IF NOT EXISTS "BINS" (
                "TIMESTAMP"     TEXT NOT NULL,
                "WEIGHT"        REAL,
                "DISTANCE"      REAL
        );
        ''')
        conn.execute("INSERT INTO BINS (TIMESTAMP,WEIGHT,DISTANCE)\nVALUES ('{}',{},{})".format(timestamp,weight,distance))
        conn.commit()
        conn.close()

def update_tippers(WEIGHT_SENSOR_ID, WEIGHT_TYPE, ULTRASONIC_SENSOR_ID, ULTRASONIC_TYPE, HEADERS, BININFO):
        conn = sqlite3.connect("/home/pi/ZBinData/zotbin.db")
        cursor = conn.execute("SELECT TIMESTAMP, WEIGHT, DISTANCE from BINS")
        d = []
        for row in cursor:
                timestamp,weight,distance = row
                try:
                        #weight sensor data
                        if weight != "NULL":
                                d.append( {"timestamp": timestamp, "payload": {"weight": weight}, "sensor_id" : WEIGHT_SENSOR_ID,"type": WEIGHT_TYPE})
                                wt_ping = 0 #reset number of null weights
                        #ultrasonic sensor data
                        if distance != "NULL" and not timed_out:
                                d.append({"timestamp": timestamp,"payload": {"distance": distance},"sensor_id" : ULTRASONIC_SENSOR_ID,"type": ULTRASONIC_TYPE})
                                ut_ping = 0 #reset number of failed ultrasonic attempts
                        upload_time = 0 #reset number of failed updates
                except Exception as e:
                        print ("Tippers probably disconnected: ", e)
                        upload_time = upload_time+1
                        return
        r = requests.post(BININFO["tippersurl"], data=json.dumps(d), headers=HEADERS)
        if DISPLAY: update_log("query status: "+str(r.status_code)+str(r.text))
        #after updating tippers delete from local database
        conn.execute("DELETE from BINS")
        conn.commit()
        
def fail_check():
        prev_ut,prev_wt,prev_on = err_state
        if not connected:
                try:
                        check_network = checkLocalConnection('localhost',80)
                        check_internet = checkServerConnection('tippers',0)
                except TimeoutError:
                        return
        if ut_on != prev_ut and ut_ping == 0:
                ut_on = prev_ut
        if wt_on != prev_on and wt_ping == 0:
                wt_on = prev_wt
        err_state = (ut_on,wt_on,connected)

def checkLocalConnection(n,p):
        return
def checkServerConnection(n,p):
        return

def update_log(n_text:str):
        if not log:
                print(n_text+'\n')
        log_file = 0
        try:
                file = Path("zbinlog.txt")
                if(file.is_file()):
                        log_file = file.open('a')
                else:
                        log_file = file.open('w')
                log_file.write(n_text+'\n')
        except:
                print("Could not finish log\n")
        finally:
                if log_file != 0:
                        log_file.close


if __name__ == "__main__":
        main()
