from picamera import PiCamera
from time import sleep

#create camera object
camera = PiCamera()
#warm up camera
camera.start_preview()
sleep(5)
#take a picture
camera.capture('image.jpg')
#close camera
camera.stop_preview()
