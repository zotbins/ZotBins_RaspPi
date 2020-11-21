"""
Ultrasonic HC-SR04 Sensor Driver
Must be run on Raspberry Pi to work
"""

import RPi.GPIO as GPIO
import time
import signal

class HCSR04:
    SPEED_OF_SOUND = 34300

    def __init__(self, trigger_pin: int, echo_pin: int):
        """
        trigger_pin<int>: Pin number on microcontroller that is attached to "TRIG" of HC_SR04
        echo_pin<int>: Pin number on microcontroller that is attached to "ECHO" of HC_SR04
        """
        self._trigger_pin = trigger_pin
        self._echo_pin = echo_pin

        # General GPIO setup
        GPIO.setmode(GPIO.BCM)

        # Set up ultrasonic GPIO pins
        GPIO.setup(self._trigger_pin, GPIO.OUT) 
        GPIO.setup(self._echo_pin, GPIO.IN) 

    def measure_dist(self):
        """
        Sends pulse on TRIG and converts pulse time to distance using speed of sound constant
        
        Returns NULL if sensor timed out after 5 seconds
        """
        time_elapsed = self.send_pulse()

        if time_elapsed == "NULL":
            return "NULL"

        distance = (time_elapsed * SPEED_OF_SOUND)/2
        return distance

    def _send_pulse(self)-> float:
        """
        Send 10 us pulse on TRIG pin and returns pulse time measured from ECHO pin
        """ 

        # Send 10 us pulse
        GPIO.output(self._trigger_pin, True)
        time.sleep(0.00001)
        GPIO.output(self._trigger_pin, False)

        start_time = time.time()
        stop_time = time.time()

        # Measure time of ECHO pulse and return NULL if failed
        try:
            with self.time_limit(5):
                while GPIO.input(self._echo_pin) == 0:
                    start_time = time.time()
                while GPIO.input(self._echo_pin) == 1:
                    stop_time = time.time()
        except Timeout:
            return "NULL"

        return stop_time - start_time

    @contextmanager
    def time_limit(self,seconds):
        """
        This is for the timed signal to limit the amount of time it takes for
        a function to run.
        """
        def signal_handler(signum, frame):
            raise TimeoutException("Timed out!")
        signal.signal(signal.SIGALRM, self._handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)

    def _handler(self,sig,frame):
        """
        This is for the timed signal to limit the amount of time it takes for
        a function to run.
        """
        raise Timeout

    class Timeout(Exception):
        """
        This is for the timed signal excpetion
        """
        pass
