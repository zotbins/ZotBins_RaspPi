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
JSONPATH = "../binData2.json"#"/home/pi/ZBinData/binData.json"
ERRPATH = "../errData.json"#"/home/pi/ZBinData/errData.json"

MAXTIMEOUT = 5    #default value for sensor timeout

class ZState():
    """
    tracks the statuses of each sensor (on/off)
    For reference (tentatively):
    ultra:      ultrasonic sensors
    weight:     load sensor
    tippers:    connection

    sensorOn<{bool}>:   tracks each sensor's functionality
        U<bool>:    local value that tracks whether the ultrasonic sensor is working
        W<bool>:    local value that tracks whether the weight sensor is working
        T<bool>:    local value that tracks whether there is online connection
    sensorCount<{int}>: counts the number of failed sensor attempts
        U<int>:counts the number of failed ultrasonic attempts
        W<int>:counts the number of faulty load sensing readings
        T<int>:counts the number of failed connection attempts
    sensorMax<{int}>:   tracks each sensor's tolerance value before deeming failure
        U<int>:  the max number of failed attempts before sonic sensor is deemed "not working"
        W<int>:  the max number of failed attempts before load sensor is deemed "not working"
        T<int>:  the max number of failed attempts before connection is lost
    """

    #sensorID = {}      replace once sensorID's is added to ZBinClassDev
    def __init__(self,sensors:list=[],enabled=True,notif=True):
        """
        pass in values for the current ZotBin sensor configuration. A set of tolerance
        values are chosen from a separate file.
        enabled<bool>: default max values will be read from .json file if True
        notif<bool>:  email notifications will be sent if True
        """
        self.sensorOn,self.sensorCount,self.sensorMax = {},{},{} #initialize the 3 dict from above
        self.sensorID = sensors
        self.sensor_setup(enabled)


    def sensor_setup(self,enabled=False):
        """
        sets up the ZState's error tolerances from an external file. If enabled
        is False or the file is not found then a list of default values are chosen
        **(currently configured for weight and ultrasonic sensor only!!!)
        """
        if enabled:
            with open(JSONPATH) as bindata:
                stateinfo = eval( bindata.read() )["bin"][1]
            for id in self.sensorID:
                self.sensorMax[id] = stateinfo[id]
        else:
            for id in self.sensorID:
                self.sensorMax[id] = MAXTIMEOUT
            #change to dictionary settings later ^^

    def check(self,output=True):
        """
        Checks the ZState to see if the @Count falls within a certain @Max threshold
        If @Count is > @Max, this will update the @ to False and double the @Max threshold
        as well as log a warning for email notifications.
        Returns false if nothing went wrong
        output<bool>:   will report notification if True #not used

        """
        iState = self.sensorOn.copy() #saves the previous state to prevent duplicate notifications
        state_change = False #flags if the state has changed due to a sensor's Count exceeding its Max threshold
        for key,value in self.sensorCount.items():
            if value > self.sensorMax[key]:
                self.sensorOn[key] = False
                self.sensorMax[key] *= 2

                #if there is a change in state, report it. Also ignores sensors are default set to false (old version)
                if iState[key]!=self.sensorOn[key] and output:
                    self.report(key)
                    state_change = True
        #self.print()
        if state_change:
            return True
        else:
            return False

    def increment(self,sensorID:str,amount:int=1):
        """
        increments the sensor's failure count by the amount provided
        """
        self.sensorCount[sensorID] += amount

    def reset(self,sensorID:str,enabled=False):
        """
        Will reset the sensor associated with @ character
        sensorID<str>:  contains the @ character
        enabled<bool>:  will reset @Max values from a .json file or the defined default value
        """
        self.sensorOn[sensorID] = True
        self.sensorCount[sensorID] = 0
        if enabled:
            with open(JSONPATH) as bindata:
                sensorinfo = eval( bindata.read() )["bin"][1]
            self.sensorMax[sensorID] = sensorinfo[sensorID]
        else:
            self.sensorMax[sensorID] = MAXTIMEOUT
        return

    def report(self,sensorID:str,lvl:int=0):
        """
        Will log and notify changes to the sensor.
        sensorID<str>:  contains the @ character
        notif<bool>:  will send an email notification if True (Recommended for sensor failures)
        """
        errorlog = {}
        with open(ERRPATH) as logdata:
            errorlog = eval( logdata.read() )["messages"][0]

        if sensorID in errorlog.keys():
            logging.warning(errorlog[sensorID][lvl])
        else:
            logging.warning(errorlog["default"][lvl].format(sensorID))

    #currently broken
    def checkConnection(self,time_out=100,link="www.google.com"):
        """
        Default: checks to see if there is a valid connection to the gmail smtp_server.
        Can also check online connection to a site
        timeout<int>:   wait time (mS) trying to connect to the link
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
        with open(JSONPATH) as emaildata:
            EMAILINFO = eval( emaildata.read())["user"][0]


        if r == "" or r == None:
            emailTarget = EMAILINFO["target"][0] #no recipient
        else:
            emailTarget = r #assume valid email

        smtp_server = "smtp.gmail.com"
        port = 465
        login_user = EMAILINFO["email"]
        login_pass = EMAILINFO["pass"]
        context = ssl.create_default_context()

        #email packaging
        msg_to = emailTarget
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
                currline = a.readline()
                msg_text += currline
        except:
            if msg_text == None: #include a default message if not present
                msg_text += "See Bin for more details"
        msg.attach(MIMEText("Pi Error Notification,"plain"))

        try:
            with smtplib.SMTP_SSL(smtp_server,port,context=context) as server:
                server.login(login_user,login_pass)
                server.sendmail(msg_from,msg_to,msg_text)

        except Exception as e:
            logging.exception(e)
            return

    #for debugging purposes:
    def print(self):
        for sensor in self.sensorOn.keys():
            print(self.sensorOn[sensor],self.sensorCount[sensor],self.sensorMax[sensor],sep=";",end='\n')

'''FUTURE CODE USE
'''
