#!/usr/bin/env python3

# Inspired from: https://simonprickett.dev/playing-with-raspberry-pi-door-sensor-fun/

import RPi.GPIO as GPIO
import time
import sys, os
import signal

DOOR_SENSOR_PIN = 18

# Set Broadcom mode so we can address GPIO pins by number.
GPIO.setmode(GPIO.BCM)

# Initially we don't know if the door sensor is open or closed...
isOpen = None
oldIsOpen = None

# Clean up when the user exits with keyboard interrupt
def cleanup(signal, frame):
    print("Exiting...")
    GPIO.cleanup()
    sys.exit(0)

# Set up the door sensor pin.
GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down = GPIO.PUD_UP)

# Set the cleanup handler for when user hits Ctrl-C to exit
signal.signal(signal.SIGINT, cleanup)

print("Listening to the door state change...")

while True:
    oldIsOpen = isOpen
    isOpen = GPIO.input(DOOR_SENSOR_PIN)

    if (isOpen and (isOpen != oldIsOpen)):
        print("Door is open")
        os.system('echo "Hello, friend." | mail -s "Door opened!" root@localhost')
    elif (isOpen != oldIsOpen):
        print("Door is closed")
        os.system('echo "Hello, friend." | mail -s "Door closed" root@localhost')

    time.sleep(0.1)
