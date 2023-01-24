#!/usr/bin/env python3

import json
import requests
import redis
import signal
import sys

thread = None
pubsub = None

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    if (thread != None):
      thread.stop()
      thread.join(timeout=1.0)
      pubsub.close()
      print('Gracefully exiting...')

red = redis.Redis('localhost', 6379, charset="utf-8", decode_responses=True)

def door_status_change(message):
  door_status = message['data']
  print('Door status received:', door_status)

if __name__ == "__main__":
  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)
  #while True:
  #print(sys.argv[1])
  pubsub = red.pubsub()
  pubsub.subscribe(**{'door_status': door_status_change})
  thread = pubsub.run_in_thread(sleep_time=0.001)
  print("Awaiting door status changes...")
