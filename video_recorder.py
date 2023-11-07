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

from picamera2.encoders import H264Encoder
from picamera2.outputs import CircularOutput
from picamera2 import Picamera2, MappedArray
from libcamera import Transform
from libcamera import controls

import cv2

import turn_led

REPO_PATH = os.path.join(os.path.dirname(__file__))
SEND_EMAIL_SCRIPT_PATH = os.path.join(REPO_PATH, 'send-email.sh')

format_logs = "%(asctime)s: %(message)s"
logging.basicConfig(stream=sys.stdout, format=format_logs, level=logging.INFO)

fps=10

thread = None
pubsub = None

# Constants for displaying the timestamp on the video
colour = (0, 255, 0)
origin = (0, 30)
font = cv2.FONT_HERSHEY_SIMPLEX
scale = 1
thickness = 2

picam2 = Picamera2()

def apply_timestamp(request):
    timestamp = time.strftime("%Y-%m-%d %X")
    with MappedArray(request, "main") as m:
        cv2.putText(m.array, timestamp, origin, font, scale, colour, thickness)

def signal_handler(sig, frame):
    logging.info('You pressed Ctrl+C!')
    logging.info('Gracefully exiting...')
    if (thread != None):
      thread.stop()
      thread.join(timeout=1.0)
      pubsub.close()

    turn_led.cleanup()
    picam2.stop_encoder()
    logging.info('Encoder stopped')
    picam2.stop()
    logging.info('Camera stoppped')

red = redis.Redis('localhost', 6379, charset="utf-8", decode_responses=True)

size=(1280, 720)

conf = picam2.create_video_configuration(main={"size": size, "format": "RGB888"}, transform=Transform(hflip=True,vflip=True), controls={"FrameRate": float(fps), "AfMode": controls.AfModeEnum.Continuous, "NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Off})
picam2.configure(conf)
picam2.pre_callback = apply_timestamp
one_mega_bits_per_second=1_000_000
encoder = H264Encoder(one_mega_bits_per_second, repeat=True, framerate=float(fps), enable_sps_framerate=True)
duration=5 # seconds
encoder.output = CircularOutput(buffersize=int(fps * (duration + 0.2)))
picam2.encoder = encoder
picam2.start() # Start the cam only
picam2.start_encoder()

def alarm_state():
  return red.get('alarm_state') == '1'

def door_status_change(message):
  door_status = message['data']
  logging.info('Door status received:' + door_status)
  if door_status == 'open' or door_status == 'still_open' or door_status == 'motion':
      now = time.strftime("%Y-%m-%dT%H:%M:%S")

      alarm_enabled = alarm_state()

      if alarm_enabled:
        # subprocess.Popen is non blocking
        if door_status == 'open':
          subprocess.Popen([SEND_EMAIL_SCRIPT_PATH, "Door just opened!"])
        elif door_status == 'still_open':
          subprocess.Popen([SEND_EMAIL_SCRIPT_PATH, "Door still open"])
        elif door_status == 'motion':
          subprocess.Popen([SEND_EMAIL_SCRIPT_PATH, "Motion detected"])
        else:
          subprocess.Popen([SEND_EMAIL_SCRIPT_PATH, f"Alert! Received: {door_status}"])

      turn_led.turn_on()

      photo1 = f"/tmp/{now}-1.jpg"
      picam2.capture_file(photo1)
      if alarm_enabled:
        subprocess.Popen([SEND_EMAIL_SCRIPT_PATH, "Alarm - photo 1", photo1])

      logging.info('Recording...')
      filename = f'/tmp/{now}.h264'
      encoder.output.fileoutput = filename
      encoder.output.start()

      time.sleep(5) # 5 seconds of video this far
      photo2 = f"/tmp/{now}-2.jpg"
      picam2.capture_file(photo2)
      if alarm_enabled:
        subprocess.Popen([SEND_EMAIL_SCRIPT_PATH, "Alarm - photo 2", photo2])

      time.sleep(5) # 10 seconds of video this far
      photo3 = f"/tmp/{now}-3.jpg"
      picam2.capture_file(photo3)
      if alarm_enabled:
        subprocess.Popen([SEND_EMAIL_SCRIPT_PATH, "Alarm - photo 3", photo3])

      time.sleep(5) # 15 seconds of video this far

      encoder.output.stop()
      turn_led.turn_off()
      logging.info("Done recording")
      final_filename = f"{filename}.mp4"
      os.system(f"ffmpeg -r {fps} -i {filename} -vcodec copy {final_filename}")
      if alarm_enabled:
        subprocess.Popen([SEND_EMAIL_SCRIPT_PATH, "Alarm - video", final_filename])
      logging.info('Ffmpeg done')

if __name__ == "__main__":
  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)
  pubsub = red.pubsub()
  pubsub.subscribe(**{'door_status': door_status_change})
  thread = pubsub.run_in_thread(sleep_time=0.001)
  logging.info(f"Script is located in {REPO_PATH}")
  logging.info("Awaiting order to record video...")
