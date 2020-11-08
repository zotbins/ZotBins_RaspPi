"""
Authors: David Pham
Notes:
- This is meant to be run with Python 3.5+
- PLEASE CHECK FOR AN UPDATE .JSON file. This will fail with it!!
Resources:
- Some of the code here was used from other projects/tutorials
- ultrasonic resource: https://tutorials-raspberrypi.com/raspberry-pi-ultrasonic-sensor-hc-sr04/
- load cell resources:
"""
#=====logging import===========
import logging

#=====email imports=========
from email import encoders
from email.message import Message
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

#=====network imports=======
import ssl, http.client
from socket import *

#=====file imports=====
from pathlib import Path
SIMULATE = True

if not SIMULATE:
    JSON_PATH = "/home/pi/ZBinData/binData.json"
else:
    JSON_PATH = "./simulation/binData.json"
ERR_PATH = "/home/pi/ZBinData/errData.json"

MAX_TIMEOUT = 5    #default value for sensor timeout

class ZState():
    """
    tracks the statuses of each sensor (on/off)
    For reference (tentatively):
    ultra:      ultrasonic sensors
    weight:     load sensor
    tippers:    connection
    sensor_ON<{bool}>:   tracks each sensor's functionality
        U<bool>:    local value that tracks whether the ultrasonic sensor is working
        W<bool>:    local value that tracks whether the weight sensor is working
        T<bool>:    local value that tracks whether there is online connection
    sensor_count<{int}>: counts the number of failed sensor attempts
        U<int>:counts the number of failed ultrasonic attempts
        W<int>:counts the number of faulty load sensing readings
        T<int>:counts the number of failed connection attempts
    sensor_max<{int}>:   tracks each sensor's tolerance value before deeming failure
        U<int>:  the max number of failed attempts before sonic sensor is deemed "not working"
        W<int>:  the max number of failed attempts before load sensor is deemed "not working"
        T<int>:  the max number of failed attempts before connection is lost
    """

    #sensor_ID = {}      replace once sensor_ID's is added to ZBinClassDev
    def __init__(self,sensors:list=[],enabled=True,notif=True):
        """
        pass in values for the current ZotBin sensor configuration. A set of tolerance
        values are chosen from a separate file.
        enabled<bool>: default max values will be read from .json file if True
        notif<bool>:  email notifications will be sent if True
        """
        self.sensor_ON,self.sensor_count,self.sensor_max = {},{},{} #initialize the 3 dict from above
        self.sensor_ID = sensors
        self.sensor_setup(enabled)


    def sensor_setup(self,enabled=False):
        """
        sets up the ZState's error tolerances from an external file. If enabled
        is False or the file is not found then a list of default values are chosen
        **(currently configured for weight and ultrasonic sensor only!!!)
        """
        self.sensor_ON = { k:True for k in self.sensor_ID}
        self.sensor_count = {k:0 for k in self.sensor_ID}

        if enabled:
            with open(JSON_PATH) as bindata:
                state_info = eval( bindata.read() )["bin"][1]
            for id in self.sensor_ID:
                self.sensor_max[id] = state_info[id]
        else:
            for id in self.sensor_ID:
                self.sensor_max[id] = MAX_TIMEOUT
            #change to dictionary settings later ^^

    def check(self,output=True):
        """
        Checks the ZState to see if the @Count falls within a certain @Max threshold
        If @Count is > @Max, this will update the @ to False and double the @Max threshold
        as well as log a warning for email notifications.
        Returns false if nothing went wrong
        output<bool>:   will report notification if True #not used

        """
        i_state = self.sensor_ON.copy() #saves the previous state to prevent duplicate notifications
        state_change = False #flags if the state has faulted due to a sensor's fail Count exceeding its Max threshold
        states = [] #stores the error messages of the faulted sensors
        for key,value in self.sensor_count.items():
            if value > self.sensor_max[key]:
                self.sensor_ON[key] = False
                self.sensor_max[key] *= 2

                #if there is a change in state, report it.
                if i_state[key]!=self.sensor_ON[key] and output:
                    states.append[self.report(key)]
                    state_change = True

        if state_change:
            return states
        else:
            return "NULL"

    def increment(self,sensor_ID:str,amount:int=1):
        """
        increments the sensor's failure count by the amount provided
        """
        self.sensor_count[sensor_ID] += amount

    def reset(self,sensor_ID:str,enabled=False):
        """
        Will reset the sensor associated with @ character
        sensor_ID<str>:  contains the @ character
        enabled<bool>:  will reset @Max values from a .json file or the defined default value
        """
        self.sensor_ON[sensor_ID] = True
        self.sensor_count[sensor_ID] = 0
        if enabled:
            with open(JSON_PATH) as bindata:
                sensorinfo = eval( bindata.read() )["bin"][1]
            self.sensor_max[sensor_ID] = sensorinfo[sensor_ID]
        else:
            self.sensor_max[sensor_ID] = MAX_TIMEOUT
        return

    def report(self,sensor_ID:str,lvl:int=0):
        """
        Will log and notify changes to the sensor. Returns the error message as str
        sensor_ID<str>:  contains the @ character
        notif<bool>:  will send an email notification if True (Recommended for sensor failures)
        """
        error_log = {}
        msg = ""
        with open(ERR_PATH) as log_data:
            error_log = eval( log_data.read() )["messages"][0]

        if sensor_ID in error_log.keys():
            msg = error_log[sensor_ID][lvl]
        else:
            msg = error_log["default"][lvl].format(sensor_ID)
        logging.warning(msg)
        return msg

    def checkConnection(self,time_out=100,link="www.google.com"):
        """
        Default: checks to see if there is a valid connection to the gmail smtp_server.
        Can also check online connection to a site
        timeout<int>:  wait time (mS) trying to connect to the link
        """
        h = http.client.HTTPConnection("www.gmail.com",timeout=time_out)
        try:
            h.request("HEAD","/")
            response = h.getresponse()
            return True
        except TimeoutError:
            logging.warning(" Connection timed out.")
            self.increment("tippers")
            return False
        except ConnectionError:
            logging.warning(" Connection was denied.")
            self.increment("tippers")
            return False
        except Exception as e:
            logging.warning("",e)
            return False
        finally:
            h.close()



    def notify(message:str=None,directory:Path=None, r=None):
        """
        sends an email notification to the specified recipient

        level<{str}>:   speciifies the type of email at the subject. Default topics
                        can be pulled from the error.json or input (if doesn't exist)
            error
            report
            update
        message<str>:   a message that will be sent with the email
        file<Path>:     specify a file that will be sent. Usually the log file
        r<str>:         specifies the recipient of the email
        """
        with open(JSON_PATH) as email_data:
            EMAIL_INFO = eval( email_data.read())["user"][0]


        if r == "" or r == None:
            email_target = EMAIL_INFO["target"][0] #no recipient
        else:
            email_target = r #assume valid email

        smtp_server = "smtp.gmail.com"
        port = 465
        login_user = EMAIL_INFO["email"]
        login_pass = EMAIL_INFO["pass"]
        context = ssl.create_default_context()

        #email packaging
        msg_to = email_target
        msg_from = login_user
        msg_head = "Pi Notification"

        #formatting email
        msg = MIMEMultipart()
        msg["To"] = msg_to
        msg["From"] = msg_from
        msg["Subject"] = msg_head

        msg_text = message
        try:
            #directory only takes in a file PATH
            with open(directory,"rb") as a:
                curr_line = a.readline()
                msg_text += curr_line
        except:
            if msg_text == None: #include a default message if not present
                msg_text += "See Bin for more details"
        msg.attach(MIMEText("Pi Error Notification","plain"))

        try:
            with smtplib.SMTP_SSL(smtp_server,port,context=context) as server:
                server.login(login_user,login_pass)
                server.sendmail(msg_from,msg_to,msg_text)

        except Exception as e:
            logging.exception(e)
            return

    #for debugging purposes:
    def print(self):
        for sensor in self.sensor_ON.keys():
            print(self.sensor_ON[sensor],self.sensor_count[sensor],self.sensor_max[sensor],sep=";",end='\n')

'''FUTURE CODE USE
'''
