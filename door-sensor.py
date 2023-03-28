#!/usr/bin/env python3

# Inspired from: https://simonprickett.dev/playing-with-raspberry-pi-door-sensor-fun/

import RPi.GPIO as GPIO
import time
import sys, os
import signal
import redis
import requests
import importlib

config = importlib.import_module('config').get_config()

url=config.get('weatherstation', 'GOOGLE_SCRIPTS_WEATHER_URL')

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

while True:
    oldIsOpen = isOpen
    isOpen = GPIO.input(DOOR_SENSOR_PIN)

    if (isOpen != oldIsOpen):
        door_status = 'open' if isOpen else 'closed'
        print("Door is currently " + door_status)

        r.publish('door_status', door_status)

        now = time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())
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
                os.system('echo "Failed to post to Google." | mail -s "Door opened!" root@localhost')
            else:
                os.system('echo "Failed to post to Google." | mail -s "Door closed" root@localhost')

    time.sleep(0.1)
