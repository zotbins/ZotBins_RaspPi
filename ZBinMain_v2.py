# Danny's Note: probably missing libraries
# =====PyQt Related Imports======
from PyQt5 import QtCore
from PyQt5.QtCore import QThread, QTimer
# ======timestamps imports=======
import time
import datetime
# ====data collection imports====
import sys
import RPi.GPIO as GPIO
# =========API imports===========
import json
import requests
# ======weight sensor imports====
from hx711 import HX711
# =========other imports=========
import sqlite3

# ============GLOBAL VARIABLES============
# GPIO port numbers
BREAKBEAM = 4   		# break beam sensor in
HX711IN = 5				# weight sensor in
HX711OUT = 6			# weight sensor out
TRIG = 23				# ultrasonic sensor in
ECHO = 24				# ultrasonic sensor out
# Flags
DISPLAY = True  		# Print info to terminal
SEND_DATA = True		# Send data to tippers
FREQUENCY_SECONDS = 600 # wait time between calculating measurements lower time for testing, 600 seconds for actual use
# Global Filtering Variables
MAX_WEIGHT_DIFF = 11.9712793734
MAX_DIST_DIFF = 0.8
# query information
WEIGHT_TYPE = 2
ULTRASONIC_TYPE = 3
HEADERS = {
	"Content-Type": "application/json",
	"Accept": "application/json"
}


class BreakBeamThread(QThread):
	break_signal = pyqtSignal()

	def __init__(self):
		QThread.__init__(self)

	def run(self):
		while True:
			sensor_state = GPIO.input(4)
			if (sensor_state == 0):
				while(sensor_state == 0):
					sensor_state = GPIO.input(4)
				self.break_signal.emit()
				time.sleep(2) # Danny's Note: why is there a sleep here?
				#print(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))

	def __del__(self):
		self.wait()


class App(QtCore.QObject):

	bin_info
	weight_sensor_id
	ultrasonic_sensor_id
	prev_distance = 0.0 # for previous distance
	prev_weight = 0.0 # for previous weight
	post_time = time.time() # for determining when to push data

	def __init__(self):
		super(App, self).__init__()
		self.setup()

	def setup(self):
		# ============json parsing file============
		with open("/home/pi/ZBinData/binData.json") as bindata:
			self.bin_info = eval( bindata.read() )["bin"][0]
		BinID = self.bin_info["binID"]

		# ============query information============
		self.weight_sensor_id = BinID
		self.ultrasonic_sensor_id = BinID+"D"

		# ============Set up GPIOs============
		GPIO.setmode(GPIO.BCM)
		# break bean sensor
		GPIO.setup(BREAKBEAM,GPIO.IN)
		# ultrasonic
		GPIO.setup(TRIG,GPIO.OUT)
		GPIO.setup(ECHO,GPIO.IN)
		# hx711
		hx = HX711(HX711IN, HX711OUT)
		hx.set_reading_format("LSB", "MSB")
		hx.set_reference_unit(float( self.bin_info["weightCal"] ))
		hx.reset()
		hx.tare()

		# ============Threads============
		self.BreakThread = BreakBeamThread()
		self.BreakThread.start()
		self.BreakThread.break_signal.connect(self.update_local)

		# ============QTimer============
		self.timerLocal = QTimer(self)
		self.timerLocal.timeout.connect(self.update_local)
		self.timerLocal.start(300000) # 5 min

		self.timerTippers = QTimer(self)
		self.timerTippers.timeout.connect(self.update_tippers)
		self.timerTippers.start(900000) # 15 min

	def update_local(self):
		"""
		Check the ultrasonic sensor to determine if trash can is full and
		retrieve the weight and store it locally.
		"""
		_do_weight_measurement()
		_do_ultrasonic_measurement()

		# for DEBUGGING
		if DISPLAY:
			print("Weight:", self.prev_weight)
			print("Distance:", self.prev_distance, "cm")
			print("Time difference:", time.time() - self.post_time)

		# Danny's Note: This chunk of the code needs to be review 
# ------------------------------------------------------------------------------------------------
		# ============post data locally============
		timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
		add_data_to_local(timestamp, self.prev_weight, self.prev_distance)
		if DISPLAY: print("data added successfully to sqlite")
		# ============post data to Tippers============
		# check if it is time to post
		if (time.time() - self.post_time > FREQUENCY_SECONDS) and SEND_DATA: # Danny's Note: Get rid of Freq Seconds
			#update tippers with all the data from local database
			update_tippers(WEIGHT_SENSOR_ID, WEIGHT_TYPE, ULTRASONIC_SENSOR_ID, ULTRASONIC_TYPE, HEADERS, BININFO)
			self.post_time = time.time() # reset post_time
		else:
			continue # Not time to Update TIPPERS yet
# ------------------------------------------------------------------------------------------------

		self.timerLocal.start(300000) #Reset this timer, in the case that it hasn't count all the way down

	def update_tippers(self):
		conn = sqlite3.connect("/home/pi/ZBinData/zotbin.db")
		cursor = conn.execute("SELECT TIMESTAMP, WEIGHT, DISTANCE from BINS")
		d = []
		for row in cursor:
			timestamp, weight, distance = row
			try:
				#weight sensor data
				if weight != "NULL":
					d.append( {"timestamp": timestamp, "payload": {"weight": weight}, "sensor_id" : self.weight_sensor_id, "type": WEIGHT_TYPE})
				#ultrasonic sensor data
				if distance != "NULL":
					d.append({"timestamp": timestamp,"payload": {"distance": distance},"sensor_id" : self.ultrasonic_sensor_id, "type": ULTRASONIC_TYPE})
			except Exception as e:
				print ("Tippers probably disconnected: ", e)
				return
		r = requests.post(self.bin_info["tippersurl"], data=json.dumps(d), headers=HEADERS)
		if DISPLAY: print("query status: ", r.status_code, r.text)
		#after updating tippers delete from local database
		conn.execute("DELETE from BINS")
		conn.commit()

	def _do_weight_measurement():
		measurements = []
		for i in range(11):
			measurements.append(hx.get_weight(5))

		# taking median of sorted values and finding the difference
		temp_weight = sorted(measurements)[5]
		weight_diff = abs(temp_weight - self.null_check_convert(self.prev_weight))

		if DISPLAY: 
			print("\nThis is the measured weight", temp_weight)

		# filtering logic that ignores new weight reading when
		# the difference is less than a certain number
		if weight_diff < MAX_WEIGHT_DIFF:
			# the previous weight will now be the current weight
			if DISPLAY: 
				print("Weight Diff not enough:", weight_diff)
		else:
			# let the new weight be the current weight
			self.prev_weight = float(temp_weight)

		if temp_weight >= -10 and temp_weight < 0: # rounding negative numbers close to zero to zero
			self.prev_weight = 0.0
		elif temp_weight <= -10: # gets rid of inaccurate negative numbers
			hx.power_down()
			hx.power_up()
			time.sleep(.5) # Danny's Note: Shit, this might affect the QTimer in a bad way
			# Danny's Note: Ask Owen if he wanted to check for DISPLAY here before printing
			print("large negative numbers:", self.prev_weight, " on ", datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S') )
			self.prev_weight = "NULL"
			# continue # ERROR: Large Negative Numbers
			# Danny's Note: What is the line above suppose to mean? Is there things TODO?

		# reset hx711 chip 
		# Danny's Note: Why do this?
		hx.power_down()
		hx.power_up()

	def _do_ultrasonic_measurement():
		# Danny's Note: What is going on here with the outputting?
		GPIO.output(TRIG, False)

		# allowing ultrsaonic sensor to settle
		time.sleep(.5) # Danny's Note: This might affect the QTimer in a bad way
		# ultrasonic logic
		GPIO.output(TRIG, True)
		time.sleep(0.00001) # Danny's Note: This might affect the QTimer in a bad way
		GPIO.output(TRIG, False)

		# Danny's Note: Defined these first in-case they won't be defined if while True right away
		pulse_end = 0
		pulse_time = 0

		while (GPIO.input(ECHO) == 0):
			pulse_start = time.time()
			# POSSIBLE ERROR: stuck in while loop
			# Danny's Note: Sounds like code need to be added here

		while (GPIO.input(ECHO) == 1):
			pulse_end = time.time()
			# POSSIBLE ERROR: stuck in while loop
			# Danny's Note: Sounds like code need to be added here

		pulse_duration = pulse_end - pulse_start

		# collecting temporary distance and finding the difference between previous distance and current distance
		temp_distance = float(pulse_duration * 17150)
		distance_diff = abs(temp_distance - self.prev_distance)
		# logic for filtering out distance data.
		if distance_diff < MAX_DIST_DIFF and distance_diff > 0:
			pass
		else:
			self.prev_distance = round(temp_distance, 2)

	def null_check_convert(self, value):
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


if __name__ == "__main__":
	app = QtCore.QCoreApplication(sys.argv)
	ex = App()
	sys.exit(app.exec_())
