#!/usr/bin/env python3

# Inspired from: https://simonprickett.dev/playing-with-raspberry-pi-door-sensor-fun/

import RPi.GPIO as GPIO
import time
import sys, os
import signal
import redis
import datetime
import requests
import subprocess

url="https://script.google.com/macros/s/XYZ/exec"

DOOR_SENSOR_PIN = 18

# Set Broadcom mode so we can address GPIO pins by number.
GPIO.setmode(GPIO.BCM)

# Initially we don't know if the door sensor is open or closed...
isOpen = None
oldIsOpen = None

def send_request(data):
    try:
        response = requests.get(
            url,
            params={
                "datetime": data['timestamp'],
                "door_status": data['door_status'],
            },
        )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

# Clean up when the user exits with keyboard interrupt
def cleanup(signal, frame):
    print("Exiting...")
    GPIO.cleanup()
    sys.exit(0)

# Set up the door sensor pin.
GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down = GPIO.PUD_UP)

# Set the cleanup handler for when user hits Ctrl-C to exit
signal.signal(signal.SIGINT, cleanup)

r = redis.Redis('localhost', 6379, charset="utf-8", decode_responses=True)

print("Listening to the door state change...")

video_recording = None

while True:
    oldIsOpen = isOpen
    isOpen = GPIO.input(DOOR_SENSOR_PIN)

    if (isOpen != oldIsOpen):
        door_status = 'open' if isOpen else 'closed'
        print("Door is currently " + door_status)

        r.publish('door_status', door_status)

        if (isOpen) and ((video_recording == None) or (video_recording.returncode == None)):
            video_recording = subprocess.Popen(["/home/pi/raspberry-pi-security-camera/video-to-email.sh"])

        utc_offset_in_hours = int(-time.timezone/3600)
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=utc_offset_in_hours))).strftime('%d/%m/%Y %H:%M:%S')
        data = { 'timestamp': now, 'door_status': door_status }

        successfully_sent = False
        try:
            successfully_sent = send_request(data)
        except BaseException as e:
            print("Error: %s" % str(e))

        if not successfully_sent:
            print('Failed to post to Google App Script')
            print(data)
            r.rpush('door_status', str(data))
            if (isOpen):
                os.system('echo "Hello, friend." | mail -s "Door opened!" root@localhost')
            else:
                os.system('echo "Hello, friend." | mail -s "Door closed" root@localhost')

    time.sleep(0.1)
