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

DISPLAY = True

def main(SEND_DATA=True, FREQUENCY_SECONDS = 60;):
	"""
	This is the main function that collects data for the
	Raspberry Pi. This function manages data collection
	by the Raspberry Pi, performs error checking, and
	sends data to the UCI TIPPERS SERVER.
	[SEND_DATA]: a bool that turns on/off sending data to tippers
	[FREQUENCY_SECONDS] = wait time between calculating measurements lower time for testing, 600 seconds for actual use;
	"""
	#============json parsing file===================
	with open("/home/pi/ZBinData/binData.txt") as bindata:
		BININFO = eval( bindata.read() )["bin"][0]
	BinID = BININFO["binID"]
	#setting GPIO Mode for weight sensor.
	GPIO.setmode(GPIO.BCM)

	#Global Filtering Variables. If a measured weight difference is
	MAX_WEIGHT_DIFF = 11.9712793734
	MAX_DIST_DIFF = 0.8

	#GPIO port numbers
	HX711IN = 5		#weight sensor in
	HX711OUT = 6	#weight sensor out
	TRIG = 23		#ultrasonic sensor in
	ECHO = 24		#ultrasonic sensor out

	#query information
	WEIGHT_SENSOR_ID = BinID
	WEIGHT_TYPE = 2
	ULTRASONIC_SENSOR_ID = BinID+"D"
	ULTRASONIC_TYPE = 3
	HEADERS = {
		"Content-Type": "application/json",
		"Accept": "application/json"
	}

	#========================ultrasonic set up================================
	GPIO.setup(TRIG,GPIO.OUT)
	GPIO.setup(ECHO,GPIO.IN)
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

			if DISPLAY: print("\nThis is the measured weight",temp_weight)

			#filtering logic that ignores new weight reading when
			#the difference is less than a certain number
			if weight_diff < MAX_WEIGHT_DIFF:
				#the previous weight will now be the current weight
				if DISPLAY: print("Weight Diff not enough:", weight_diff)
			else:
				#let the new weight be the current weight
				weight = float(temp_weight)

			if weight>=-10 and weight<0: #rounding negative numbers close to zero to zero
				weight = 0.0
			elif weight <= -10: #gets rid of inaccurate negative numbers
				hx.power_down()
				hx.power_up()
				time.sleep(.5)
				print("large negative numbers:", weight, " on ", datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S') )
				weight = "NULL"
				#continue #ERROR: Large Negative Numbers

			#reset hx711 chip
			hx.power_down()
			hx.power_up()
			#=============end of weight collection======================

			#=============start of ultrasonic measurement===============
			GPIO.output(TRIG, False)

			#allowing ultrsaonic sensor to settle
			time.sleep(.5)
			#ultrasonic logic
			GPIO.output(TRIG, True)
			time.sleep(0.00001)
			GPIO.output(TRIG, False)

			while GPIO.input(ECHO)==0:
				pulse_start = time.time()
				#POSSIBLE ERROR: stuck in while loop

			while GPIO.input(ECHO)==1:
				pulse_end = time.time()
				#POSSIBLE ERROR: stuck in while loop

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
				print("Weight:", weight)
				print("Distance:", distance, "cm")
				print("Time difference:", time.time()-post_time)

			#===================post data locally=====================
			timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
			add_data_to_local(timestamp, weight, distance)
			if DISPLAY: print("data added successfully to sqlite")
			#====================post data to Tippers==================
			#check if it is time to post
			if (time.time() - post_time > FREQUENCY_SECONDS) and SEND_DATA:
				#update tippers with all the data from local database
				update_tippers(WEIGHT_SENSOR_ID, WEIGHT_TYPE, ULTRASONIC_SENSOR_ID, ULTRASONIC_TYPE, HEADERS, BININFO)
				post_time = time.time() #reset post_time
			else:
				continue #Not time to Update TIPPERS yet

			#=======time stall========
			time.sleep(120)

	except KeyboardInterrupt:
	    if DISPLAY: print "Cleaning..."
	    GPIO.cleanup()
	    if DISPLAY: print "Bye!"
	    sys.exit()

def null_check_convert(value):
	"""
	This function checks whether or not the given value is
	the string "NULL" and converts it to a float if necessary.
	[value]: a float or a string "NULL" that represents weight or distance data.
	"""
	if value == "NULL":
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
		"TIMESTAMP"	TEXT NOT NULL,
		"WEIGHT"	REAL,
		"DISTANCE"	REAL
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
			#ultrasonic sensor data
			if distance != "NULL":
				d.append({"timestamp": timestamp,"payload": {"distance": distance},"sensor_id" : ULTRASONIC_SENSOR_ID,"type": ULTRASONIC_TYPE})
		except Exception as e:
			print ("Tippers probably disconnected: ", e)
			return
	r = requests.post(BININFO["tippersurl"], data=json.dumps(d), headers=HEADERS)
	if DISPLAY: print("query status: ", r.status_code, r.text)
	#after updating tippers delete from local database
	conn.execute("DELETE from BINS")
	conn.commit()


if __name__ == "__main__":
	main()
