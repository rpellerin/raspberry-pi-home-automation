#!/usr/bin/env python3

import json
import requests
import redis
import signal
import sys
import time
import os
import subprocess

from picamera2.encoders import H264Encoder
from picamera2.outputs import CircularOutput
from picamera2 import Picamera2, MappedArray
from libcamera import Transform
from libcamera import controls

import cv2

import turn_led

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
    print('You pressed Ctrl+C!')
    print('Gracefully exiting...')
    if (thread != None):
      thread.stop()
      thread.join(timeout=1.0)
      pubsub.close()

    turn_led.cleanup()
    picam2.stop_encoder()
    print('Encoder stopped')
    picam2.stop()
    print('Camera stoppped')

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

def should_send_emails():
  return red.get('should_send_emails') == '1'

def door_status_change(message):
  door_status = message['data']
  print('Door status received:', door_status)
  if door_status == 'open':
      turn_led.turn_on()
      send_email = should_send_emails()

      if send_email: subprocess.Popen(["/home/pi/raspberry-pi-home-automation/email-without-attachment.sh"])

      now = time.strftime("%Y-%m-%dT%H:%M:%S")
      print(now + ': door opened! Recording...')
      filename = f'/tmp/{now}.h264'
      encoder.output.fileoutput = filename
      encoder.output.start()
      time.sleep(15) # 15 seconds of video
      encoder.output.stop()
      turn_led.turn_off()
      print(time.strftime("%Y-%m-%dT%H:%M:%S") + ": done recording")
      final_filename = f"{filename}.mp4"
      os.system(f"ffmpeg -r {fps} -i {filename} -vcodec copy {final_filename}")
      if send_email: subprocess.Popen(["/home/pi/raspberry-pi-home-automation/video-to-email.sh", final_filename])
      print('Ffmpeg done')

if __name__ == "__main__":
  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)
  pubsub = red.pubsub()
  pubsub.subscribe(**{'door_status': door_status_change})
  thread = pubsub.run_in_thread(sleep_time=0.001)
  print("Awaiting order to record video...")
