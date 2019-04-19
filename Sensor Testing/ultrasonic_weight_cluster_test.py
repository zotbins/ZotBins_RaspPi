import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
import sys
import RPi.GPIO as GPIO
from hx711 import HX711
#========================hx711 set up================
TRIG = 23
ECHO = 24
#====================================================

#========================hx711 set up=====================================
def cleanAndExit():
	#print "Cleaning..."
	GPIO.cleanup()
	#print "Bye!"
	sys.exit()

def power_nap():
        #hx.power_down()
        #hx.power_up()
        time.sleep(2)

GPIO.cleanup() #cleaning up everything before

hx = HX711(5, 6)
hx.set_reading_format("LSB", "MSB")
hx.set_reference_unit(17020/195.16)
hx.reset()
hx.tare()

GPIO.setup(TRIG,GPIO.OUT)
GPIO.setup(ECHO,GPIO.IN)
try:
	#Distance Measurement
	while True:
		GPIO.output(TRIG, False)
		time.sleep(1)

		GPIO.output(TRIG, True)
		GPIO.output(TRIG, True)
		time.sleep(0.00001)
		GPIO.output(TRIG, False)

		while GPIO.input(ECHO)==0:
			pulse_start = time.time()
		while GPIO.input(ECHO)==1:
			pulse_end = time.time()
		pulse_duration = pulse_end - pulse_start
		distance = pulse_duration * 17150
		distance = round(distance, 2)
		print()
		print("\nDistance:", distance, "cm")

		#Weight measurement
		derek = []
		for i in range(11):
			derek.append(hx.get_weight(5))
			time.sleep(.5)
		#print(sorted(derek))
		val = sorted(derek)[5]
		if val <-10: #gets rid of inaccurate negative numbers
			power_nap()
			print("large negative number detected....measuring again")
			continue
		elif val <0:
			val = 0
		print ("Weight:", val, "grams")
		power_nap()
except (KeyboardInterrupt, SystemExit):
	cleanAndExit()
