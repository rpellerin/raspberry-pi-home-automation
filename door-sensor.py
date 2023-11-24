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

CONFIG = importlib.import_module("config").get_config()
GOOGLE_SCRIPTS_WEATHER_URL = CONFIG.get("weatherstation", "GOOGLE_SCRIPTS_WEATHER_URL")
DOOR_SENSOR_PIN = 18

# Set Broadcom mode so we can address GPIO pins by number.
GPIO.setmode(GPIO.BCM)

format_logs = "%(asctime)s: %(message)s"
logging.basicConfig(stream=sys.stdout, format=format_logs, level=logging.INFO)

arduino = serial.Serial(
    "/dev/ttyACM0", 9600, timeout=1
)  # 9600 must be the same number as in the Arduino code

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
                "datetime": data["timestamp"],
                "door_status": data["door_status"],
            },
        )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        logging.error("RequestException!")
        return False
    except BaseException as error:
        logging.error("BaseException!")
        logging.error(error)
        return False


def post_to_google_scripts(data, r, last_thread):
    if last_thread != None:
        if last_thread.is_alive():
            logging.info("Waiting on previous call to Google Scripts to complete...")
        else:
            logging.info("Previous call to Google Scripts already complete")

        last_thread.join(30)
        if last_thread.is_alive():
            logging.info(
                "Previous call's thread still alive. Ignoring and proceeding..."
            )

    logging.info("Sending to Google Scripts...")

    successfully_sent = False
    try:
        successfully_sent = send_request(data)
    except BaseException as e:
        logging.error("Error: %s" % str(e))

    if successfully_sent:
        logging.info(f"Successfully posted to Google Scripts {data}")

    if not successfully_sent:
        logging.warning("Failed to post to Google Scripts")
        logging.warning(data)
        r.rpush("door_status", str(data))
        os.system(
            f'echo "{str(data)}" | mail -s "Failed to post to Google." root@localhost'
        )


# Set up the door sensor pin.
GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Set the cleanup handler for when user hits Ctrl-C to exit
signal.signal(signal.SIGINT, cleanup)

logging.info("Listening to the door state change...")

# Initially we don't know if the door sensor is open or closed...
isOpen = "unknown (script started)"
oldIsOpen = None
last_thread = None

r = redis.Redis("localhost", 6379, charset="utf-8", decode_responses=True)
current_or_future_alarm_state = r.get("alarm_state") or "unknown"
actual_current_alarm_state = current_or_future_alarm_state
set_alarm_at_time = None

ALARM_ARMED = "1"
ALARM_DISARMED = "0"

REEMIT_AFTER_SECONDS = 15.0
start_time = None
last_motion_detected_at = None
logging.info(f"Current alarm state: {actual_current_alarm_state}")

while True:
    oldIsOpen = isOpen
    isOpen = GPIO.input(DOOR_SENSOR_PIN)

    if isOpen != oldIsOpen:
        start_time = timer()

        door_status = "open" if isOpen else "closed"
        message = f"{door_status} (was {oldIsOpen})"
        logging.info("Door is currently " + message)

        r.publish("door_status", door_status)
        logging.info("Status sent to Redis")

        now = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())
        data = {"timestamp": now, "door_status": message}

        last_thread = threading.Thread(
            target=post_to_google_scripts, args=[data, r, last_thread]
        )
        last_thread.start()

    if (isOpen) and (isOpen == oldIsOpen):
        if (timer() - start_time) >= REEMIT_AFTER_SECONDS:
            start_time = timer()
            r.publish("door_status", "still_open")
            logging.info("Re-emitted status (still_open) to Redis")

    if arduino.in_waiting > 0:
        message = arduino.readline().decode("utf-8").rstrip()

        if (message == "Motion detected") and (
            actual_current_alarm_state == ALARM_ARMED
        ):
            # We detected motion, and alarm is armed
            # If the alarm is not armed, we ignore motion detection, cause that would happen all the time

            now_in_seconds = int(time.time())

            if (last_motion_detected_at == None) or (
                (last_motion_detected_at + int(REEMIT_AFTER_SECONDS)) < now_in_seconds
            ):
                # We detected motion for the first time, or it's been more than 15 secondes since the last initial detection
                last_motion_detected_at = now_in_seconds
                logging.info(f"Received from Arduino: {message}")

                # Let's raise the alarm only if the door is not already open
                if not isOpen:
                    now = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())
                    data = {"timestamp": now, "door_status": "motion detected"}
                    last_thread = threading.Thread(
                        target=post_to_google_scripts, args=[data, r, last_thread]
                    )
                    last_thread.start()
                    r.publish("door_status", "motion")

        if message == "ON pressed" or message == "OFF pressed":
            logging.info(f"Received from Arduino: {message}")
            new_alarm_state = (
                ALARM_ARMED if (message == "ON pressed") else ALARM_DISARMED
            )

            if new_alarm_state != current_or_future_alarm_state:
                if message == "ON pressed":
                    logs_message = "ON"
                    set_alarm_at_time = int(time.time()) + 30
                else:
                    logs_message = "OFF"
                    set_alarm_at_time = None
                    logging.info(f"REDIS: Set alarm_state to {ALARM_DISARMED}")
                    actual_current_alarm_state = ALARM_DISARMED
                    r.set("alarm_state", ALARM_DISARMED)

                logs_message = (
                    f"ALARM {logs_message} (was {current_or_future_alarm_state})"
                )

                logging.info(logs_message)
                current_or_future_alarm_state = new_alarm_state

                now = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())
                data = {"timestamp": now, "door_status": logs_message}
                last_thread = threading.Thread(
                    target=post_to_google_scripts, args=[data, r, last_thread]
                )
                last_thread.start()

    if (set_alarm_at_time != None) and (int(time.time()) > set_alarm_at_time):
        logging.info(f"REDIS: Set alarm_state to {ALARM_ARMED}")
        set_alarm_at_time = None
        actual_current_alarm_state = ALARM_ARMED
        r.set("alarm_state", ALARM_ARMED)

    time.sleep(0.1)
