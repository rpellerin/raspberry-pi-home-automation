#!/usr/bin/env python3

# Inspired from: https://simonprickett.dev/playing-with-raspberry-pi-door-sensor-fun/

import RPi.GPIO as GPIO
import time
import sys, os
import signal
import redis
import requests
import importlib
import threading
import logging

CONFIG = importlib.import_module('config').get_config()
GOOGLE_SCRIPTS_WEATHER_URL=CONFIG.get('weatherstation', 'GOOGLE_SCRIPTS_WEATHER_URL')
DOOR_SENSOR_PIN = 18

# Set Broadcom mode so we can address GPIO pins by number.
GPIO.setmode(GPIO.BCM)

format_logs = "%(asctime)s: %(message)s"
logging.basicConfig(format=format_logs, level=logging.INFO)

# Clean up when the user exits with keyboard interrupt
def cleanup(signal, frame):
    logging.info("Exiting...")
    GPIO.cleanup()
    sys.exit(0)

def send_request(data):
    try:
        response = requests.get(
            GOOGLE_SCRIPTS_WEATHER_URL,
            params={
                "datetime": data['timestamp'],
                "door_status": data['door_status'],
            },
        )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def post_to_google_scripts(data, isOpen, r):
    successfully_sent = False
    try:
        successfully_sent = send_request(data)
    except BaseException as e:
        logging.error("Error: %s" % str(e))

    if not successfully_sent:
        logging.warning('Failed to post to Google App Script')
        logging.warning(data)
        r.rpush('door_status', str(data))
        if (isOpen):
            os.system('echo "Failed to post to Google." | mail -s "Door opened!" root@localhost')
        else:
            os.system('echo "Failed to post to Google." | mail -s "Door closed" root@localhost')

# Set up the door sensor pin.
GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down = GPIO.PUD_UP)

# Set the cleanup handler for when user hits Ctrl-C to exit
signal.signal(signal.SIGINT, cleanup)

logging.info("Listening to the door state change...")

# Initially we don't know if the door sensor is open or closed...
isOpen = None
oldIsOpen = None

while True:
    oldIsOpen = isOpen
    isOpen = GPIO.input(DOOR_SENSOR_PIN)

    if (isOpen != oldIsOpen):
        door_status = 'open' if isOpen else 'closed'
        now = time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())
        logging.info("Door is currently " + door_status)

        r = redis.Redis('localhost', 6379, charset="utf-8", decode_responses=True)
        r.publish('door_status', door_status)
        logging.info('Status sent to Redis')

        data = { 'timestamp': now, 'door_status': door_status }

        x = threading.Thread(target=post_to_google_scripts, args=[data, isOpen, r])
        x.start()

    time.sleep(0.1)
