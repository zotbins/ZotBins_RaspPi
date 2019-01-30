import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)

TRIG = 23
ECHO = 24

print("Distance Measurement In Progress...")

GPIO.setup(TRIG,GPIO.OUT)
GPIO.setup(ECHO,GPIO.IN)
try:
	while True:
		#print("Distance Measurement In Progress")
		GPIO.output(TRIG, False)
		#print("Waiting For Sensor To Settle")
		time.sleep(1)

		GPIO.output(TRIG, True)
		GPIO.output(TRIG, True)
		time.sleep(0.00001)
		GPIO.output(TRIG, False)
		
		while GPIO.input(ECHO)==0:
			pulse_start = time.time()
			#print(pulse_start)

		while GPIO.input(ECHO)==1:
			pulse_end = time.time()
		pulse_duration = pulse_end - pulse_start

		distnace = pulse_duration * 17150

		distnace = round(distnace, 2)

		print("\nDistance:", distnace, "cm")

finally:
	GPIO.cleanup()
'''
if True:
	GPIO.output(TRIG, False)
	print("Waiting For Sensor To Settle")
	time.sleep(2)

	GPIO.output(TRIG, True)
	time.sleep(0.00001)
	GPIO.output(TRIG, False)

	while GPIO.input(ECHO)==0:
		pulse_start = time.time()
	print("pstart =" + str(pulse_start))
	while GPIO.input(ECHO)==1:
		pulse_end = time.time()
	print("pend =" + str(pulse_end))
	pulse_duration = pulse_end - pulse_start

	distnace = pulse_duration * 17150

	distnace = round(distnace, 2)

	print("Distnace:", distnace, "cm")

GPIO.cleanup()
'''
