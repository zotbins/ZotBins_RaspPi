import time
import datetime
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(4,GPIO.IN)
GPIO.setup(17,GPIO.IN)
GPIO.setup(27,GPIO.IN)



while True:
    sensor_state = GPIO.input(4)
    print(GPIO.input(4))
    if (sensor_state==0):
        while(sensor_state==0):
            sensor_state = GPIO.input(4)
            print(GPIO.input(4))
            print(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
            time.sleep(1)
    time.sleep(1)
