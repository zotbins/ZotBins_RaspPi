    
#compiled in python3#
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
import smtplib, ssl, urllib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from pathlib import Path

LOG = True #write error log
DISPLAY = True #print to display
FLAGS = True
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
        HX711OUT = 6    		#weight sensor out
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

        #configure error log settings
        log_file = error_log_set()

        #===========================debug=============================
        #warning flags and checks
        ut_ping = 0             #ultrasonic timeout keeper, increments once per ping attempt
        ut_pong = 0
        wt_ping = 0             #weight sensor timeout keeper, only increments on NULL read weights not inaccurate readings
        upload_time = 0 #number of unsuccessful uploads to tippers
        connect_time = 0 #number of unsuccessful network attempts
        
        
        WT_MAX, UT_MAXP, UT_MAXT, TIP_MAX, CT_MAX = 0,0,0,0,0
        F_MAX = setflags("/home/pi/ZotBins_RaspPi/error_readme.txt")
        MAX = F_MAX #for saving old threshold values
        
        #sensor pinging flags/counters
        pulse_ping = 0
        timed_out = False
        
        ut_on = True
        wt_on = True
        connected = True #isConnected('localhost',5050)
        err_state = True,True,True


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
                        if DISPLAY: print("starting weight")
                        #============start weight measurement================
                        #collecting a list of measurements
                        derek = []
                        for i in range(11):
                                derek.append( hx.get_weight(5) )

                        #taking median of sorted values and finding the difference
                        temp_weight = sorted(derek)[5]
                        weight_diff = abs( temp_weight - null_check_convert(weight) )
        

                        #filtering logic that ignores new weight reading when
                        #the difference is less than a certain number
                        if weight_diff < MAX_WEIGHT_DIFF:
                                #the previous weight will now be the current weight
                                pass
                        else:
                                #let the new weight be the current weight
                                weight = float(temp_weight)

                        if temp_weight>=-10 and temp_weight<0: #rounding negative numbers close to zero to zero
                                weight = 0.0
                        elif temp_weight <= -10: #gets rid of inaccurate negative numbers
                                hx.power_down()
                                hx.power_up()
                                time.sleep(.5)
                                weight = "NULL"
                                wt_ping = wt_ping + 1
                                #continue #ERROR: Large Negative Numbers

                        #reset hx711 chip
                        hx.power_down()
                        hx.power_up()
                        #=============end of weight collection======================

                        #=============start of ultrasonic measurement===============
                        GPIO.output(TRIG, False)
                        
 
                        if DISPLAY: print("starting sensing")

                        #allowing ultrsaonic sensor to settle
                        time.sleep(.5)
                        #ultrasonic logic
                        GPIO.output(TRIG, True)
                        time.sleep(0.00001)
                        GPIO.output(TRIG, False)
                        
                        #check to see if sensor is in the ready state. Gets time once ready for calculations
                        while GPIO.input(ECHO)==0 and pulse_ping < MAX_ULTRASONIC_PING:
                                pulse_start = time.time()
                                pulse_ping = pulse_ping+1

                        #checks unusual case where sensor never switches to a ready state (always receives noise feedback)
                        if pulse_ping == MAX_ULTRASONIC_PING:
                                timed_out = True
                                ut_ping = ut_ping + 1
                                
                        pulse_ping = 0 #reset pulse_ping to reuse for the 2nd part

                        while GPIO.input(ECHO)==1 and pulse_ping < MAX_ULTRASONIC_PING:
                                pulse_end = time.time()
                                pulse_ping = pulse_ping+1
                                
                        #in the case the sensor times out or never switches state, increment error state
                        if pulse_ping == MAX_ULTRASONIC_PING or timed_out:
                                timed_out = True
                                pulse_duration = 0 #what value is pulse ping if it times out??
                                ut_pong = ut_pong+1
                                if DISPLAY: print("ultrasonic timed out")
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
                        time.sleep(10)

                        #===================post data locally=====================
                        timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
                        add_data_to_local(timestamp, weight, distance)
                        if DISPLAY: update_log("data added successfully to sqlite")
                        #====================post data to Tippers==================
                        #check if it is time to post
                        #else: Not time to Update TIPPERS yet
                        if (time.time() - post_time > FREQUENCY_SECONDS) and SEND_DATA:
                                #update tippers with all the data from local database
                                update_tippers(WEIGHT_SENSOR_ID, WEIGHT_TYPE, ULTRASONIC_SENSOR_ID, ULTRASONIC_TYPE, HEADERS, BININFO)
                                post_time = time.time() #reset post_time
                        #error checking setup
                        flags = ut_ping,ut_pong,wt_ping,connect_time,upload_time
                        err_state,MAX = fail_check(err_state,flags,MAX,F_MAX,log_file)

        except KeyboardInterrupt:
            if DISPLAY: update_log("Cleaning...")
            GPIO.cleanup()
            logging.shutdown()
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
                                #reset number of failed ultrasonic attempts
                                ut_ping = 0
                                ut_pong = 0
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
'''
checks each flag to see if they fall within the fault tolerances. It will update each flag with a new threshold until the next failure. There is no max threshold, but the minimum will stay at its preset values. The function will take in the previous err_state and update it if a new failure occurs and send a new notification downloading the current error log (log_file) to email. Returns a err_state (three boolean tuple)
'''
def fail_check(prev_err,flags,MAX,old_MAX,err_log):
    #save previous err_state to prevent spamming (ie state hasn't changed)
    prev_ut,prev_wt,prev_ct = prev_err
    ut_ping,ut_pong,wt_ping,connect_time,upload_time = flags
    UT_MAXP,UT_MAXT,WT_MAX,CT_MAX,TIP_MAX = MAX
    
    if DISPLAY: print(flags)
    
    #tolerance checking
    if ut_ping > UT_MAXP:
        logging.warning("ultrasonic sensor failed to restart")
        ut_on = False
        UT_MAXP = UT_MAXP*2
    else:
        ut_on = True
        UT_MAXP = old_MAX[0]
    if ut_pong > UT_MAXT:
        ut_on = False
        logging.warning("ultrasonic sensor failed to respond")
        UT_MAXT = UT_MAXT*2
    else:
        ut_on = True
        UT_MAXT = old_MAX[1]
    if wt_ping > WT_MAX:
        wt_on = False
        logging.warning("load sensor failed to respond")
        WT_MAX = WT_MAX*2
    else:
        wt_on = True
        WT_MAX = old_MAX[2]
    if connect_time > CT_MAX:
        connected = False
        logging.warning("Pi is not connected to the network")
        CT_MAX = CT_MAX*2
    else:
        connected = True
        CT_MAX = old_MAX[3]
    if upload_time > TIP_MAX:
        connected = False
        logging.warning("Tippers failed to respond")
        TIP_MAX = TIP_MAX+5
    else:
        connected = True
        TIP_MAX = old_MAX[4]
   
    '''
        if not connected:
                try:
                        check_network = checkLocalConnection('localhost',80)
                        check_internet = checkServerConnection('tippers',0)
                except TimeoutError:
                        break
    '''
    #check to see if errstate and MAX values have changed
    if prev_err != (ut_on,wt_on,connected):
        send_notification(err_log)
        prev_err = ut_on,wt_on,connected
    MAX =  UT_MAXP,UT_MAXT, WT_MAX, CT_MAX, TIP_MAX
    return prev_err,MAX

def checkLocalConnection(n,p):
        return
def checkServerConnection(n,p):
        return

def update_log(n_text:str):
        print(n_text+'\n')

#sets up logging capture into file during start up
def error_log_set():
        err_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S') #append this to log report name
        err_log = "logs/zbinlog{}.txt".format(err_time)
        logging.basicConfig(filename=err_log, level=logging.WARNING, format='%(asctime)s %(message)s') #set log report to debugging level (10)
        logging.captureWarnings(True) #will capture all warnings to the log
        if DISPLAY: print("error log capture ON")
        return err_log


#creates a SSL connection to send an email notification w/file location as a parameter
def send_notification(directory):
    #==setting up email notif==#
    with open("/home/pi/ZBinData/binData.json") as emaildata:
            EMAILINFO = eval( emaildata.read())["bin"][1]
    emailTarget = EMAILINFO["target"][0]

    smtp_server = "smtp.gmail.com"
    port = 465
    login_user = EMAILINFO["User"]
    login_pass = EMAILINFO["Pass"]
    context = ssl.create_default_context()

    #email packaging
    msg_to = emailTarget
    msg_from = login_user
    msg_head = "Pi Notification"
    #formatting email
    msg = MIMEMultipart()
    msg["To"] = msg_to
    msg["From"] = msg_from
    msg["Subject"] = msg_head
    try:
        with open(directory,"rb") as a:
            part = MIMEBase("application","octet-stream")
            part.set_payload(a.read())
        encoders.encode_base64(part)
        msg.attach(part)
    except:
        msg.attach(MIMEText("Error notifcation",plain))

    msg_text = msg.as_string()

    try:
        with smtplib.SMTP_SSL(smtp_server,port,context=context) as server:
            server.login(login_user,login_pass)
            server.sendmail(msg_from,msg_to,msg_text)

    except Exception as e:
        logging.exception(e)
        
#reads the presets for flag limits for error tolerances
def setflags(file:str):
    """
    Sets the tolerance values for the sensors.
    """
    try:
        with open(file) as f:
            line = f.readline()
            while line != "":
                if line.strip() == "***": #skip to presets
                    WT_MAX = f.readline().split(':')[1]
                    UT_MAXP = f.readline().split(':')[1]
                    UT_MAXT = f.readline().split(':')[1]
                    TIP_MAX = f.readline().split(':')[1]
                    CT_MAX = f.readline().split(':')[1]
                    
                    '''#ignore comments for demo testing
                    if FLAGS:
                        f.readline() 
                        wt_on = f.readline().split(':')[1]
                        ut_on = f.readline().split(':')[1]
                        connected = f.readline().split(':')[1]
                       ''' 
                    return UT_MAXP,UT_MAXT, WT_MAX, CT_MAX, TIP_MAX
                line = f.readline() 
    except FileNotFoundError: 
        logging.warning(" error_readme.txt not found. Using preset values")
        WT_MAX = 5
        UT_MAXP = 1 #sees if ultrasonic sensor is not connected. if echo didn't reset.
        UT_MAXT = 1 #sees if ultrasonic sensor is not working. if it doesn't receive.
        TIP_MAX = 5
        CT_MAX = 10
        return UT_MAXP,UT_MAXT, WT_MAX, CT_MAX, TIP_MAX
    except Exception as e:
        logging.exception("Expected error_readme.txt file in directory")
            

if __name__ == "__main__":
        main()
