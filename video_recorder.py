#!/usr/bin/env python3

import json
import requests
import redis
import signal
import sys
import time
import os
import logging
import subprocess
import importlib
import threading

from picamera2.encoders import H264Encoder  # python3-picamera2
from picamera2.outputs import CircularOutput  # python3-picamera2
from picamera2 import Picamera2, MappedArray  # python3-picamera2
from libcamera import Transform
from libcamera import controls

import cv2  # python3-opencv

import home_automation.turn_led as turn_led
from home_automation.config import PUSHOVER_USER
from home_automation.config import PUSHOVER_TOKEN

REPO_PATH = os.path.join(os.path.dirname(__file__))
SEND_EMAIL_SCRIPT_PATH = os.path.join(REPO_PATH, "send-email.sh")

format_logs = "%(asctime)s: %(message)s"
logging.basicConfig(stream=sys.stdout, format=format_logs, level=logging.INFO)

fps = 10

thread = None
pubsub = None

# Constants for displaying the timestamp on the video
colour = (0, 255, 0)
origin = (0, 30)
font = cv2.FONT_HERSHEY_SIMPLEX
scale = 1
thickness = 2

picam2 = Picamera2()

PUSHOVER_URL = "https://api.pushover.net/1/messages.json"

# WATCHDOG
# The camera library relies on compiled C++ that can crash without "letting the Python code know about it",
# leaving our script in a frozen state, that appears to be running, from the systemctl service viewpoint.
# Hence we need to implement a watchdog to properly kill our Python script when an error has occured
# deep into C++ code.
watchdog_lock = threading.Lock()
current_task = None
task_start_time = 0
WATCHDOG_TIMEOUT = 25  # Seconds before considering it frozen

def watchdog_worker():
    """Background thread that monitors if any operation is taking too long."""
    global current_task, task_start_time
    while True:
        time.sleep(2)  # Check every 2 seconds
        with watchdog_lock:
            if current_task is not None:
                elapsed = time.time() - task_start_time
                if elapsed > WATCHDOG_TIMEOUT:
                    logging.critical(f"WATCHDOG TRIGGERED: Task '{current_task}' has been frozen for {elapsed:.1f} seconds!")
                    logging.critical("Hardware or driver has locked up. Forcing process exit for systemd restart...")
                    os._exit(1)

def set_watchdog_task(task_name):
    global current_task, task_start_time
    with watchdog_lock:
        current_task = task_name
        task_start_time = time.time()

def clear_watchdog_task():
    global current_task
    with watchdog_lock:
        current_task = None

def post_to_pushover(message, attachment):
    if (PUSHOVER_USER == None) or (PUSHOVER_TOKEN == None):
        logging.warning("Missing env vars to send to Pushover")
        return

    payload = {
        "user": PUSHOVER_USER,
        "token": PUSHOVER_TOKEN,
        "message": message,
        "priority": 1,  # High priority
    }

    try:
        if (attachment) and (attachment.endswith(".jpg")):
            response = requests.post(
                PUSHOVER_URL,
                data=payload,
                files={
                    "attachment": (
                        "image.jpg",
                        open(attachment, "rb"),
                        "image/jpeg",
                    )
                },
                timeout=20,
            )
        else:
            response = requests.post(
                PUSHOVER_URL, data=payload, timeout=20
            )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        logging.error("RequestException!")
        return False
    except BaseException as error:
        logging.error("BaseException!")
        logging.error(error)
        return False

# Sends an email and a Pushover notification
def post_message(message, push_notification_too, attachment=""):
    logging.info("Sending to Pushover")
    # subprocess.Popen is non blocking
    subprocess.Popen([SEND_EMAIL_SCRIPT_PATH, message, attachment])
    logging.info("Sending over email")
    if push_notification_too:
        threading.Thread(target=post_to_pushover, args=[message, attachment]).start()
    logging.info("Done sending")


def apply_timestamp(request):
    timestamp = time.strftime("%Y-%m-%d %X")
    with MappedArray(request, "main") as m:
        cv2.putText(m.array, timestamp, origin, font, scale, colour, thickness)

def stop_camera_and_led():
    turn_led.cleanup()
    picam2.stop_encoder()
    logging.info("Encoder stopped")
    picam2.stop()
    logging.info("Camera stoppped")

def signal_handler(sig, frame):
    logging.info("You pressed Ctrl+C!")
    logging.info("Gracefully exiting...")
    if thread != None:
        thread.stop()
        thread.join(timeout=1.0)
        pubsub.close()

    stop_camera_and_led()


watchdog_thread = threading.Thread(target=watchdog_worker, daemon=True)
watchdog_thread.start()

redis_instance = redis.Redis("localhost", 6379, decode_responses=True)

size = (1280, 720)

conf = picam2.create_video_configuration(
    main={"size": size, "format": "RGB888"},
    transform=Transform(hflip=True, vflip=True),
    controls={
        "FrameRate": float(fps),
        "AfMode": controls.AfModeEnum.Continuous,
        "NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Off,
    },
)
picam2.configure(conf)
picam2.pre_callback = apply_timestamp
one_mega_bits_per_second = 1_000_000
encoder = H264Encoder(
    one_mega_bits_per_second,
    repeat=True,
    framerate=float(fps),
    enable_sps_framerate=True,
)
duration = 5  # seconds
encoder.output = CircularOutput(buffersize=int(fps * (duration + 0.2)))
picam2.start()  # Start the cam only
picam2.start_encoder(encoder)


def alarm_state():
    return redis_instance.get("alarm_state") == "1"


def door_status_change(message):
    set_watchdog_task("door_status_change")
    # This entire function runs in a background Redis pub/sub thread.
    # We wrap the *entire* function in a try/except because if ANY unhandled exception
    # (e.g. redis.ConnectionError, picamera hardware failure, GPIO error) kills this thread,
    # the main Python process will NOT exit (because picamera2 maintains its own non-daemon threads).
    # This would result in a zombie process that systemd thinks is healthy.
    # Catching everything and calling os._exit(1) forces the entire process to die so systemd restarts it.
    try:
        door_status = message["data"]
        logging.info("Door status received: " + door_status)
        if door_status == "open" or door_status == "still_open" or door_status == "motion":
            now = time.strftime("%Y-%m-%dT%H:%M:%S")

            alarm_enabled = alarm_state()

            if alarm_enabled:
                if door_status == "open":
                    post_message("Door just opened!", push_notification_too=True)
                elif door_status == "still_open":
                    post_message("Door still open", push_notification_too=True)
                elif door_status == "motion":
                    post_message("Motion detected", push_notification_too=True)
                else:
                    post_message(
                        f"Alert! Received: {door_status}", push_notification_too=True
                    )

            turn_led.turn_on()

            photo1 = f"/tmp/{now}-1.jpg"
            logging.info("Taking photo 1...")
            # Use capture_array() instead of capture_file() while encoder is running
            img1 = picam2.capture_array()
            cv2.imwrite(photo1, img1)
            logging.info("Photo 1 taken")
            if alarm_enabled:
                post_message(
                    "Alarm - photo 1", push_notification_too=True, attachment=photo1
                )

            logging.info("Recording...")
            filename = f"/tmp/{now}.h264"
            encoder.output.fileoutput = filename
            encoder.output.start()

            time.sleep(5)  # 5 seconds of video this far
            photo2 = f"/tmp/{now}-2.jpg"
            logging.info("Taking photo 2...")
            img2 = picam2.capture_array()
            cv2.imwrite(photo2, img2)
            logging.info("Photo 2 taken")

            if alarm_enabled:
                post_message(
                    "Alarm - photo 2", push_notification_too=True, attachment=photo2
                )

            time.sleep(5)  # 10 seconds of video this far
            photo3 = f"/tmp/{now}-3.jpg"
            logging.info("Taking photo 3...")
            img3 = picam2.capture_array()
            cv2.imwrite(photo3, img3)
            logging.info("Photo 3 taken")
            if alarm_enabled:
                post_message(
                    "Alarm - photo 3", push_notification_too=True, attachment=photo3
                )

            time.sleep(5)  # 15 seconds of video this far

            encoder.output.stop()
            turn_led.turn_off()
            logging.info("Done recording")
            final_filename = f"{filename}.mp4"
            os.system(f"ffmpeg -r {fps} -i {filename} -vcodec copy {final_filename}")
            if alarm_enabled:
                post_message(
                    "Alarm - video", push_notification_too=False, attachment=final_filename
                )
            logging.info("Ffmpeg done")

    except Exception as e:
        # Catch any hardware timeout, Redis disconnect, etc.
        logging.critical(f"Unrecoverable error in recording pipeline: {e}")

        # Clean up what we can before dying
        try:
            stop_camera_and_led()
        except Exception:
            pass # Hardware might be totally unresponsive, ignore secondary failures

        logging.critical("Forcing script exit to allow systemd restart...")
        # os._exit immediately kills the main process from a sub-thread
        os._exit(1)
    finally:
        clear_watchdog_task()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    pubsub = redis_instance.pubsub()
    pubsub.subscribe(**{"door_status": door_status_change})
    thread = pubsub.run_in_thread(sleep_time=0.001)
    logging.info(f"Script is located in {REPO_PATH}")
    logging.info(subprocess.check_output("df -h", shell=True).decode("utf-8"))
    logging.info("Awaiting order to record video...")
