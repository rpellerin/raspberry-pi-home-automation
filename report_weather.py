import smbus2
import bme280
import time
import requests
import datetime
import sys
import redis
import json
import importlib

config = importlib.import_module('config').get_config()

url=config.get('weatherstation', 'GOOGLE_SCRIPTS_WEATHER_URL')

port = 1
address = 0x76
bus = smbus2.SMBus(port)
utc_offset_in_hours = int(-time.timezone/3600)
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=utc_offset_in_hours))).strftime('%d/%m/%Y %H:%M:%S')

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
