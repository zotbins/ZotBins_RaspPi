import serial
import time

ser = serial.Serial('/dev/ttyACM0',9600)

while True:
    try:
        read_serial=ser.readline()
        print(str(read_serial, 'utf-8').rstrip())
    except serial.serialutil.SerialException:
        time.sleep(2)
