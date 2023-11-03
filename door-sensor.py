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
from timeit import default_timer as timer
import serial

CONFIG = importlib.import_module('config').get_config()
GOOGLE_SCRIPTS_WEATHER_URL=CONFIG.get('weatherstation', 'GOOGLE_SCRIPTS_WEATHER_URL')
DOOR_SENSOR_PIN = 18

# Set Broadcom mode so we can address GPIO pins by number.
GPIO.setmode(GPIO.BCM)

format_logs = "%(asctime)s: %(message)s"
logging.basicConfig(stream=sys.stdout, format=format_logs, level=logging.INFO)

arduino = serial.Serial("/dev/ttyACM0", 9600, timeout=1) # 9600 must be the same number as in the Arduino code

# Flush any byte that could already be in the input buffer,
# to avoid receiving weird/not useful/not complete data at the beginning of the communication.
arduino.reset_input_buffer()

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

def post_to_google_scripts(data, r, last_thread):
    if last_thread != None:
        if last_thread.is_alive():
            logging.info("Waiting on previous call to Google Scripts to complete...")
        else:
            logging.info("Previous call to Google Scripts already complete")

        last_thread.join()

    logging.info("Sending to Google Scripts...")

    successfully_sent = False
    try:
        successfully_sent = send_request(data)
    except BaseException as e:
        logging.error("Error: %s" % str(e))

    if successfully_sent:
        logging.info(f'Successfully posted to Google Scripts {data}')

    if (not successfully_sent):
        logging.warning('Failed to post to Google Scripts')
        logging.warning(data)
        r.rpush('door_status', str(data))
        os.system(f'echo "{str(data)}" | mail -s "Failed to post to Google." root@localhost')

# Set up the door sensor pin.
GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down = GPIO.PUD_UP)

# Set the cleanup handler for when user hits Ctrl-C to exit
signal.signal(signal.SIGINT, cleanup)

logging.info("Listening to the door state change...")

# Initially we don't know if the door sensor is open or closed...
isOpen = 'unknown (script started)'
oldIsOpen = None
last_thread = None

r = redis.Redis('localhost', 6379, charset="utf-8", decode_responses=True)
latest_alarm_state = r.get('alarm_state') or 'unknown'
set_alarm_at_time = None

REEMIT_AFTER_SECONDS = 15.0
start_time = None

while True:
    oldIsOpen = isOpen
    isOpen = GPIO.input(DOOR_SENSOR_PIN)

    if (isOpen != oldIsOpen):
        start_time = timer()

        door_status = 'open' if isOpen else 'closed'
        message = f"{door_status} (was {oldIsOpen})"
        logging.info("Door is currently " + message)

        r.publish('door_status', door_status)
        logging.info('Status sent to Redis')

        now = time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())
        data = { 'timestamp': now, 'door_status': message }

        last_thread = threading.Thread(target=post_to_google_scripts, args=[data, r, last_thread])
        last_thread.start()

    if (isOpen) and (isOpen == oldIsOpen):
        if ((timer() - start_time) >= REEMIT_AFTER_SECONDS):
            start_time = timer()
            r.publish('door_status', 'open')
            logging.info('Re-emitted status (open) to Redis')

    if (arduino.in_waiting > 0):
        message = arduino.readline().decode('utf-8').rstrip()
        logging.info(f"Receveid from Arduino: {message}")

        if message == 'ON pressed' or message == 'OFF pressed':
            new_alarm_state = '1' if (message == 'ON pressed') else '0'

            if new_alarm_state != latest_alarm_state:
                if (message == 'ON pressed'):
                    logs_message = 'ON'
                    set_alarm_at_time = int(time.time()) + 30
                else:
                    logs_message = 'OFF'
                    set_alarm_at_time = None
                    logging.info('REDIS: Set alarm_state to 0')
                    r.set('alarm_state', '0')

                logs_message = f"ALARM {logs_message} (was {latest_alarm_state})"

                logging.info(logs_message)
                latest_alarm_state = new_alarm_state

                now = time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())
                data = { 'timestamp': now, 'door_status': logs_message }
                last_thread = threading.Thread(target=post_to_google_scripts, args=[data, r, last_thread])
                last_thread.start()

    if (set_alarm_at_time != None) and (int(time.time()) > set_alarm_at_time):
        logging.info('REDIS: Set alarm_state to 1')
        set_alarm_at_time = None
        r.set('alarm_state', '1')

    time.sleep(0.1)
