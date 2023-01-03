#!/usr/bin/env python3

# Inspired from: https://simonprickett.dev/playing-with-raspberry-pi-door-sensor-fun/

import RPi.GPIO as GPIO
import time
import sys, os
import signal
import redis
import datetime

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

r = redis.Redis()

print("Listening to the door state change...")

while True:
    oldIsOpen = isOpen
    isOpen = GPIO.input(DOOR_SENSOR_PIN)

    if (isOpen != oldIsOpen):
        utc_offset_in_hours = int(-time.timezone/3600)
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=utc_offset_in_hours))).strftime('%d/%m/%Y %H:%M:%S')
        if (isOpen):
            print("Door is open")
            r.rpush('door_status', str({ 'timestamp': now, 'status': 'open', 'old_is_open': oldIsOpen}))
            os.system('echo "Hello, friend." | mail -s "Door opened!" root@localhost')
        else:
            print("Door is closed")
            r.rpush('door_status', str({ 'timestamp': now, 'status': 'closed', 'old_is_open': oldIsOpen}))
            os.system('echo "Hello, friend." | mail -s "Door closed" root@localhost')

    time.sleep(0.1)
