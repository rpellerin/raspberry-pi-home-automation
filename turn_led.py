import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

def turn_off():
    #GPIO.setwarnings(False)
    GPIO.setup(23,GPIO.OUT) # 8th PIN on the external ROW of GPIO pins
    GPIO.output(23,GPIO.LOW)
    print("LED off")

def turn_on():
    GPIO.setup(23,GPIO.OUT) # 8th PIN on the external ROW of GPIO pins
    GPIO.output(23,GPIO.HIGH)
    print("LED on")

def cleanup():
    GPIO.cleanup()
    print('LED cleaned up')
