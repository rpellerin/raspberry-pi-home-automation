#!/bin/env -S sh -c '"`dirname $0`/.venv/bin/python3" "$0" "$@"'

# This script can be invoked in two different ways with the same result:
# $ /path/to/raspberry-pi-home-automation/report_weather.py (thanks to the complex shebang above)
# $ /path/to/raspberry-pi-home-automation/.venv/bin/python3 /path/to/raspberry-pi-home-automation/report_weather.py

import smbus2
import bme280
import time
import requests
import redis
import json
import importlib

config = importlib.import_module('config').get_config()

url=config.get('weatherstation', 'GOOGLE_SCRIPTS_WEATHER_URL')

port = 1
address = 0x76
bus = smbus2.SMBus(port)
now = time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())

calibration_params = bme280.load_calibration_params(bus, address)
def send_request(data):
    try:
        response = requests.get(
            url,
            params={
                "datetime": data['timestamp'],
                "temperature": data['temperature'],
                "humidity": data['humidity'],
                "pressure": data['pressure'],
            },
        )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


if __name__ == '__main__':
    raw_data = bme280.sample(bus, address, calibration_params)
    data = { 'timestamp': now, 'temperature': raw_data.temperature, 'humidity': raw_data.humidity, 'pressure': raw_data.pressure }

    r = redis.Redis()
    r.lpush('weather_reports', json.dumps(data))
    r.ltrim('weather_reports', 0, 9999) # No more than 10,000 elements stored in Redis

    successfully_sent = False

    try:
        successfully_sent = send_request(data)
    except BaseException as e:
        print("Error: %s" % str(e))

    if not successfully_sent:
        print('Failed to post to Google App Script')
        print(data)
