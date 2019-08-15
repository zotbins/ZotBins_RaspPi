# PyQt Related
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QGridLayout
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QPropertyAnimation, QPointF, pyqtProperty, Qt, QTread, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QPixmap
from random import randint
# Timestamps
import time
import datetime
# Data Collection
import sys
import RPi.GPIO as GPIO
# API
import json
import requests
# Weight Sensor
from hx711 import HX711
# Other
import sqlite3
from socket import *
import urllib
import logging


# =======================GLOBAL VARIABLES=======================
# GPIO port numbers
BREAKBEAM         = 4           # Break bean sensor in
HX711IN           = 5           # Weight sensor in
HX711OUT          = 6           # Weight sensor out
TRIG              = 23          # Ultrasonic sensor in
ECHO              = 24          # Ultrasonic sensor out
# Flags
DISPLAY           = True        # Print info to terminal
LOG               = False       # Write error log
SEND_DATA         = True        # Send data to tippers
FREQUENCY_SECONDS = 600         # Wait time between calculating measurements. Lower for testing. 600 seconds for actual use
# Global Filtering Variables
MAX_WEIGHT_DIFF   = 11.9712793734
MAX_DIST_DIFF     = 0.8
# Query Information
WEIGHT_TYPE       = 2
ULTRASONIC_TYPE   = 3
HEADERS           = {"Content-Type": "application/json"
                    "Accept": "application/json"}
# Bin Type
R_ID              = None        # compost, recycling, landfill, None


class WasteImage(QLabel):
    def __init__(self, parent, image_file):
        super().__init__(parent)
        self.image_file = image_file

        pix = QPixmap(self.image_file)
        pix = pix.scaled(2000.000 / 10, 6000.000 / 10, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)

        self.setPixmap(pix)

    def new_pos(self, x, y):
        self.move(x, y)

    def new_size(self, h, w):
        pix = QPixmap(self.image_file)
        pix = pix.scaled(h, w, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.setPixmap(pix)

    def _set_pos(self, pos):
        self.move(pos.x(), pos.y())

    pos = pyqtProperty(QPointF, fset=_set_pos)


class BreakBeamThread(QThread):
    break_signal = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)

    def run(self):
        while True:
            sensor_state = GPIO.input(BREAKBEAM)
            if (sensor_state == 0):
                while (sensor_state == 0):
                    sensor_state = GPIO.input(BREAKBEAM)
                self.break_signal.emit()
                time.sleep(60)
                #print(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))

    def __del__(self):
        self.wait()


class App(QWidget):
    stop_signal = pyqtSignal()
    wait_signal = False  # boolean to be used to wait between animations
    animation_num = 1  # int to be used to start an animation

    def __init__(self):
        super().__init__()  # inheritance from QWidget
        self.title = 'PyQT Window'

        # determines screen size
        screenSize = QtWidgets.QDesktopWidget().screenGeometry(-1)  # -1 = main monitor, 1 = secondary monitor

        # determines where the window will be created
        self.left = 50
        self.top = 50

        # determines the size of the window
        self.width = screenSize.width()
        self.height = screenSize.height()
        self.imageIndex = 0

        # determines background color of the window
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # initialized the window
        self.initUI()

        # run ZotBin Code
        self.zb_run()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # =============Threads================
        self.BreakThread = BreakBeamThread()
        self.BreakThread.start()
        self.BreakThread.break_signal.connect(self.printHello)
        # self.statusBar().showMessage('Message in statusbar.')

         # ======= all list defined here ========
        self.images_list = []
        self.dialog_list = []
        self.img_anim = []
        self.dialog_anim = []

        # ======= reading json files ===========
        with open('images.json') as json_file:
            data = json.load(json_file)
        self.images_size = len(data[R_ID]['images'])
        self.dial_size = len(data[R_ID]['dialogue'])
        # =======creating the Image Lables=======
        for obj in data[R_ID]['images']:
            self.images_list.append(WasteImage(self, obj))

        for obj in data[R_ID]['dialogue']:
            self.dialog_list.append(WasteImage(self, obj))

        # ======== new dimensions of pictures =========#

        # Review: Seems to be like this loop could be combine with the loop that creates the image labels
        for obj in self.images_list:
            obj.new_size(self.width / 1.5, self.height / 1.5)

        for obj in self.dialog_list:
            obj.new_pos(self.width / 5.5, 10)
            obj.new_size(self.width/ 1.5, self.height / 1.5)
        # define QPropertyAnimation Objects

        # image animations
        for obj in self.images_list:
            self.img_anim.append(QPropertyAnimation(obj, b"pos"))

        # dialog animations
        for obj in self.dialog_list:
            self.dialog_anim.append(QPropertyAnimation(obj, b"pos"))

        # hide the animations initially
        self.hide_all()

        # defining the animations
        for obj in self.img_anim:
            obj.setDuration(2000)
            obj.setStartValue(QPointF(10,self.height / 4))
            obj.setEndValue(QPointF((self.width / 3.5), self.height / 4))

        for obj in self.dialog_anim:
            obj.setDuration(2000)
            obj.setStartValue(QPointF((self.width / 5.5), 10))
            obj.setEndValue(QPointF((self.width / 5.5), self.height / 3))

        # =====Displaying the Background Frame Image===========
        background = QLabel(self)
        back_pixmap = QPixmap(data[R_ID]['background'][0])  # image.jpg (5038,9135)
        back_pixmap = back_pixmap.scaled(self.width, self.height)
        background.setPixmap(back_pixmap)

        # =====Starting the animation========
        # self.WasteImage1.show()
        # self.waste_anim1.start()
        # print(self.waste_anim1.state())
        # print(self.waste_anim1.totalDuration())

        # ============QTimer============
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.change_image)
        self.timer.start(5000)

        # ====Showing Widget======
        self.showFullScreen() #uncomment this later. We do want fullscreen, but after we have a working image
        #self.show()  # uncomment if you don't want fullscreen.

    def change_image(self):
        self.hide_all()
        self.imageIndex += 1
        if self.imageIndex >= self.images_size:
            self.imageIndex = 0
        x = self.imageIndex
        self.images_list[x].show()
        self.img_anim[x].start()

    def hide_all(self):
        for obj in self.images_list:
            obj.hide()
        for obj in self.dialog_list:
            obj.hide()

    # Review: I really don't like this function name
    def printHello(self):
        n = randint(0, self.dial_size - 1)
        self.hide_all()
        self.timer.stop()
        self.dialog_list[n].show()      # start the animation of the selected dialogue
        self.dialog_anim[n].start()
        self.timer.start(5000)

    def zb_run(self):
        # ============json parsing file============
        with open("/home/pi/ZBinData/binData.json") as bindata:
            self.bin_info = eval( bindata.read() )["bin"][0]
        BinID = self.bin_info["binID"]

        # ============query information============
        WEIGHT_SENSOR_ID = BinID
        ULTRASONIC_SENSOR_ID = BinID+"D"

        # ============Set up GPIOs============
        GPIO.setmode(GPIO.BCM)
        # break bean sensor
        GPIO.setup(BREAKBEAM,GPIO.IN)
        # ultrasonic
        GPIO.setup(TRIG,GPIO.OUT)
        GPIO.setup(ECHO,GPIO.IN)
        MAX_ULTRASONIC_PING = 100; #~1ms 
        # hx711
        hx = HX711(HX711IN, HX711OUT)
        hx.set_reading_format("LSB", "MSB")
        hx.set_reference_unit(float( self.bin_info["weightCal"] ))
        hx.reset()
        hx.tare()

        # ===========================debug=============================
        # warning flags and checks
        ut_ping = 0     #ultrasonic timeout keeper, increments once per ping attempt
        wt_ping = 0     #weight sensor timeout keeper, only increments on NULL read weights not inaccurate readings
        upload_time = 0 #number of unsuccessful uploads to tippers

        UT_MAX = 50
        WT_MAX = 100
        
        ut_on = True
        wt_on = True
        connected = True #isConnected('localhost',5050)
        err_state = (True,True,True)

        # error log settings
        err_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S') #append this to log report name
        logging.basicConfig(level=10, filename='logs/zbinlog{}.txt'.format(err_time) ) #set log report to debugging level (10)

        # ====================loop Variables==============================
        # local vairables for previous weight and distance
        distance, weight = 0.0, 0.0
        # local variable for determining when to push data
        post_time = time.time()

        try:
            while True:
                if DISPLAY: print("starting weight")
                #============start weight measurement================
                #collecting a list of measurements
                derek = [] # Review, why is this called derek
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
                    #continue #ERROR: Large Negative Numbers

                #reset hx711 chip
                hx.power_down()
                hx.power_up()
                #=============end of weight collection======================

                #=============start of ultrasonic measurement===============
                GPIO.output(TRIG, False)
                
                #sensor pinging flags/counters 
                pulse_ping = 0
                timed_out = False
                if DISPLAY: 
                    print("starting sensing")

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
                    
                pulse_ping = 0 #reset pulse_ping to reuse for the 2nd part

                while GPIO.input(ECHO)==1 and pulse_ping < MAX_ULTRASONIC_PING:
                    pulse_end = time.time()
                    pulse_ping = pulse_ping+1
                        
                #in the case the sensor times out or never switches state, increment error state
                if pulse_ping == MAX_ULTRASONIC_PING or timed_out:
                    timed_out = True
                    pulse_duration = 0 #what value is pulse ping if it times out??
                    ut_ping = ut_ping+1
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
        print(n_text+'\n')



if __name__ == "__main__":
    # determines type of animations (compost, reycle, or landfill)
    with open('binType.txt','r') as f:
        R_ID = f.read().strip()
        
    # creating new class
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_()) # 'exec_' because 'exec' is already a keyword