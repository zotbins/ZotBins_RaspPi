#experiments.py
import time
import sys
import RPi.GPIO as GPIO
from hx711 import HX711



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

def raw_weight_experiment():
	#local variables to store weight
	zero_values = []
	weight_values = []

    GPIO.setmode(GPIO.BCM)
    hx = HX711(5, 6)
    hx.set_reading_format("LSB", "MSB")
    hx.set_reference_unit(17020/195.16)
    hx.reset()
    hx.tare()
    #====================================================
    try:
    	for i in range(100):
    #============weight measurement zero====================
            val = hx.get_weight(5)
			zero_values.append(val)
    		power_nap()

		_ = input("Proceed to next test, add your weight.")

    	for i in range(100):
    #============weight measurement not zero====================
    		val = hx.get_weight(5)
			weight_values.append(val)
			power_nap()
		return [zero_values, weight_values]

    except (KeyboardInterrupt, SystemExit):
    	cleanAndExit()

if __name__ == '__main__':
	results = raw_weight_experiment()
	print(results)
