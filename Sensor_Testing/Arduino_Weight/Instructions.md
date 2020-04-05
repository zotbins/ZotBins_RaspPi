# Instructions for Raspberry Pi Receiving Arduino Weight Readings

This documentation file will give you a brief interview of how to get weight readings from the Arduino to the Raspberry Pi. We will connect a Arduino UNO to the Raspberry Pi 3 B+. The Arduino will then send the weight readings to the Raspberry Pi using serial communication through a USB Cable.

## Find the Reference Unit to Calibrate your Weight Scale
Assuming that you already have finished making your weight scale with the HX711 chip, you now need to find the reference unit to calibrate your scale.
1. Open up your [Arduino IDE](https://www.arduino.cc/en/Main/Software)
2. In your Arduino IDE open up the file find `findWeightReference.ino` from this current folder.
3. Compile and Upload your program into the Arduino.
4. Open up the Serial Monitor. Follow the instructions on the Serial Monitor to calibrate your scale.
>*You should have nothing on the scale when you first start. Then you add your weight and send "a" to increase the reference unit or "s" to decrease the reference unit. Once your reference unit correctly outputs the right weight reading, you have found your reference unit!*
5. Once you find your reference value, edit the file `weightTest.ino` and change the reference_unit variable to the value you found in step 4.

## Running the Example Code on Arduino
After you found reference unit and changed the `weightTest.ino` file to use your reference unit you should be able to run `weight Test.ino` now.
1. Open up `weightTest.ino` in the Arduino IDE.
2. Compile and Upload
3. Open up the Serial Monitor and you should be able to view the weight readings (in lbs.)

Something you should know is that the weight scale automatically sets itself to zero every time the program is re-run. So you should make sure that no extra weight is added (except the weight of a empty bin) when you start running the program.

## Reading the Weight Readings with the Raspberry Pi
Before you follow these steps, make sure you close the Serial Monitor from the Arduino IDE. You might as well close the Arduino IDE as well, we won't need it in this step. We will now read the Arduino readings using the Raspberry Pi.
1. Make sure `weightTest.ino` is compiled and uploaded to your Arduino and make sure the Weight Scale is already connected to the Arduino
2. Connect the Arduino to the Raspberry Pi with a USB cable
3. Run the code in the terminal on the Raspberry Pi:
```
python3 serialWeightReading.py
```
