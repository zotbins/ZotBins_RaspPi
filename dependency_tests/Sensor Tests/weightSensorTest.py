import numpy as np
import time
import sys
import RPi.GPIO as GPIO
from hx711 import HX711

CALLIBRATE = True
collected_vals = []

GPIO.setmode(GPIO.BCM)

#========================hx711 set up=====================================
def cleanAndExit():
	print "Cleaning..."
	GPIO.cleanup()
	print "Bye!"
	sys.exit()

def power_nap():
        #hx.power_down()
        #hx.power_up()
        time.sleep(0.5)

def test(refer_unit):
	"""
	This is the function that runs the test for
	the weight sensor.
	HOW TO CALCULATE THE REFFERENCE UNIT
	1) Set reference unit to 1
	2) put 100 gram weight on sensor
	3) take the reading and divide it by 100. Take that result and set it as our new reference.
	ex: If 2000 grams is 184000 then 1000 grams is 184000 / 2000 = 92.
	"""
	hx = HX711(5, 6)
	hx.set_reading_format("LSB", "MSB")
	hx.set_reference_unit(refer_unit)
	hx.reset()
	hx.tare()
	#====================================================

	try:
		while True:
	#============weight measurement====================

			if CALLIBRATE:
				weight = hx.get_weight(5)
				collected_vals.append(weight)
				print(weight)

			else:
				derek = []
				for i in range(11):
					#print(hx.get_weight(5))
					derek.append(hx.get_weight(5))
				#print(sorted(derek))
				val = sorted(derek)[5]
				if val <-10: #gets rid of inaccurate negative numbers
					power_nap()
					print("Large negative number:", val)
					continue
				elif val <0:
					val = 0
				print ("Weight:", val)
				collected_vals.append(val)
				power_nap()

	except (KeyboardInterrupt, SystemExit):
		if CALLIBRATE:
			print("\n")
			for i in sorted(collected_vals):
				print(i)
			print("This is the mean:", np.mean(collected_vals) )
			print("This is the median:", np.median(collected_vals) )
		print("Saving output values to file")
		try:
			outfile = open("weightSensorTestResults.txt","w")
			outfile.write(str(collected_vals))
		finally:
			outfile.close()
		cleanAndExit()

if __name__ == "__main__":
	test(1)
