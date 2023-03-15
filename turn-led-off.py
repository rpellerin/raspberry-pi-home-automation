import RPi.GPIO as GPIO

def run():
    GPIO.setmode(GPIO.BCM)
    #GPIO.setwarnings(False)
    GPIO.setup(23,GPIO.OUT) # 8th PIN on the external ROW of GPIO pins
    GPIO.output(23,GPIO.LOW)
    print("LED off")
    GPIO.cleanup()

if __name__ == "__main__":
    run()
