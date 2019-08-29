# PyQt Related
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QGridLayout
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QPropertyAnimation, QPointF, pyqtProperty, Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QPixmap
from random import randint
# Timestamps
import time
import datetime
# Data Collection
import sys
#import RPi.GPIO as GPIO
# API
import json
import requests
# Weight Sensor
#from hx711 import HX711
# Other
import sqlite3
import subprocess


# Global Variables 
R_ID = 'recycle'    # compost, recycle, landfill, None
DISPLAY = True

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


# class BreakBeamThread(QThread):
#     break_signal = pyqtSignal()

#     def __init__(self):
#         QThread.__init__(self)

#     def run(self):
#         while True:
#             sensor_state = GPIO.input(BREAKBEAM)
#             if (sensor_state == 0):
#                 while (sensor_state == 0):
#                     sensor_state = GPIO.input(BREAKBEAM)
#                 self.break_signal.emit()
#                 time.sleep(60)
#                 #print(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))

#     def __del__(self):
#         self.wait()


class BreakBeamThread(QThread):
    break_signal = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)

    def run(self):
        i = 0
        while True:
            if (i % 3 == 0 and i > 0):
                self.break_signal.emit()
            i = randint(11, 100)
            print(i)
            time.sleep(2)

    def __del__(self):
        self.wait()


class ZotBinThread(QThread):

    def __init__(self):
        QThread.__init__(self)

    def run(self):
        """
        This is the main function that collects data for the
        Raspberry Pi. This function manages data collection
        by the Raspberry Pi, performs error checking, and
        sends data to the UCI TIPPERS SERVER.
        [SEND_DATA]: a bool that turns on/off sending data to tippers
        [FREQUENCY_SECONDS] = wait time between calculating measurements lower time for testing, 600 seconds for actual use;
        """
        #============json parsing file===================
        # Replace - with open("/home/pi/ZBinData/binData.json") as bindata:
        with open("binData.json") as bindata:
            BININFO = eval( bindata.read() )["bin"][0]
        BinID = BININFO["binID"]
        # #setting GPIO Mode for weight sensor.
        # GPIO.setmode(GPIO.BCM)

        #Global Filtering Variables. If a measured weight difference is
        MAX_WEIGHT_DIFF = 11.9712793734
        MAX_DIST_DIFF = 0.8

        #GPIO port numbers
        HX711IN = 5     #weight sensor in
        HX711OUT = 6    #weight sensor out
        TRIG = 23       #ultrasonic sensor in
        ECHO = 24       #ultrasonic sensor out

        #query information
        WEIGHT_SENSOR_ID = BinID
        WEIGHT_TYPE = 2
        ULTRASONIC_SENSOR_ID = BinID+"D"
        ULTRASONIC_TYPE = 3
        HEADERS = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # #========================ultrasonic set up================================
        # GPIO.setup(TRIG,GPIO.OUT)
        # GPIO.setup(ECHO,GPIO.IN)
        # #========================hx711 set up=====================================
        # hx = HX711(HX711IN, HX711OUT)
        # hx.set_reading_format("LSB", "MSB")
        # hx.set_reference_unit(float( BININFO["weightCal"] ))
        # hx.reset()
        # hx.tare()

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
                    # derek.append( hx.get_weight(5) )
                    derek.append( 100 ) # For testing purposes

                #taking median of sorted values and finding the difference
                temp_weight = sorted(derek)[5]
                weight_diff = abs( temp_weight - self.null_check_convert(weight) )

                if DISPLAY:
                    print("\nThis is the measured weight",temp_weight)

                #filtering logic that ignores new weight reading when
                #the difference is less than a certain number
                if weight_diff < MAX_WEIGHT_DIFF:
                    #the previous weight will now be the current weight
                    if DISPLAY:
                        print("Weight Diff not enough:", weight_diff)
                else:
                    #let the new weight be the current weight
                    weight = float(temp_weight)

                if temp_weight>=-10 and temp_weight<0: #rounding negative numbers close to zero to zero
                    weight = 0.0
                elif temp_weight <= -10: #gets rid of inaccurate negative numbers
                    # hx.power_down()
                    # hx.power_up()
                    time.sleep(.5)
                    print("large negative numbers:", weight, " on ", datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S') )
                    weight = "NULL"
                    #continue #ERROR: Large Negative Numbers

                #reset hx711 chip
                # hx.power_down()
                # hx.power_up()
                #=============end of weight collection======================

                #=============start of ultrasonic measurement===============
                # GPIO.output(TRIG, False)

                #allowing ultrsaonic sensor to settle
                time.sleep(.5)
                #ultrasonic logic
                # GPIO.output(TRIG, True)
                # time.sleep(0.00001)
                # GPIO.output(TRIG, False)

                # while GPIO.input(ECHO)==0:
                #     pulse_start = time.time()
                #     #POSSIBLE ERROR: stuck in while loop

                # while GPIO.input(ECHO)==1:
                #     pulse_end = time.time()
                #     #POSSIBLE ERROR: stuck in while loop

                # pulse_duration = pulse_end - pulse_start
                pulse_duration = 2

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

                #=======time stall========
                time.sleep(120)

                #===================post data locally=====================
                timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
                self.add_data_to_local(timestamp, weight, distance)
                if DISPLAY: print("data added successfully to sqlite")
                #====================post data to Tippers==================
                #check if it is time to post
                if (time.time() - post_time > FREQUENCY_SECONDS) and SEND_DATA:
                    #update tippers with all the data from local database
                    self.update_tippers(WEIGHT_SENSOR_ID, WEIGHT_TYPE, ULTRASONIC_SENSOR_ID, ULTRASONIC_TYPE, HEADERS, BININFO)
                    post_time = time.time() #reset post_time
                else:
                    continue #Not time to Update TIPPERS yet

        except KeyboardInterrupt:
            if DISPLAY: print ("Cleaning...")
            GPIO.cleanup()
            if DISPLAY: print ("Bye!")
            sys.exit()

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

    def add_data_to_local(self, timestamp, weight, distance):
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

    def update_tippers(self, WEIGHT_SENSOR_ID, WEIGHT_TYPE, ULTRASONIC_SENSOR_ID, ULTRASONIC_TYPE, HEADERS, BININFO):
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
        self.ZotThread = ZotBinThread()
        self.ZotThread.start()
        # # hides the cursor
        # self.setCursor(Qt.BlankCursor)

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # =============Threads================
        self.BreakThread = BreakBeamThread()
        self.BreakThread.start()
        self.BreakThread.break_signal.connect(self.call_dialog)
        # self.statusBar().showMessage('Message in statusbar.')

         # ======= all list defined here ========
        self.images_list = []
        self.dialog_list = []
        self.img_anim = []
        self.dialog_anim = []

        # =======creating the Image Lables=======   
        foldername = "images/" + R_ID + "/image_ani/"
        t = subprocess.run("ls {}*.png".format(foldername),shell=True, stdout=subprocess.PIPE)
        self.images_list = t.stdout.decode('utf-8').strip().split('\n')
        self.images_list = [WasteImage(self,obj) for obj in self.images_list] #now a list of image WasteImages
        self.images_size = len(self.images_list)
        
        foldername = "images/" + R_ID + "/dialog_ani/"
        t = subprocess.run("ls {}*.png".format(foldername),shell=True, stdout=subprocess.PIPE)
        self.dialog_list = t.stdout.decode('utf-8').strip().split('\n')
        self.dialog_list = [WasteImage(self,obj) for obj in self.dialog_list]
        self.dial_size = len(self.dialog_list)

        # ======== new dimensions of pictures =========#
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
        back_pixmap = QPixmap("images/" + R_ID + "/background.png")  # image.jpg (5038,9135)
        back_pixmap = back_pixmap.scaled(self.width, self.height)
        background.setPixmap(back_pixmap)

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

    def call_dialog(self):
        n = randint(0, self.dial_size - 1)
        self.hide_all()
        self.timer.stop()
        self.dialog_list[n].show()      # start the animation of the selected dialogue
        self.dialog_anim[n].start()
        self.timer.start(5000)
        
    

if __name__ == "__main__":
    # # determines type of animations (compost, reycle, or landfill)
    # with open('binType.txt','r') as f:
    #     R_ID = f.read().strip()
        
    # creating new class
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_()) # 'exec_' because 'exec' is already a keyword
