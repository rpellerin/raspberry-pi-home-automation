import smbus2
import bme280
import time
import requests
import datetime
import sys
import redis

url="https://script.google.com/macros/s/XYZ/exec"

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
successfully_sent = False

try:
    successfully_sent = send_request(data)
except BaseException as e:
    print("Error: %s" % str(e))

if not successfully_sent:
    print('Failed to post to Google App Script')
    print(data)
    r = redis.Redis()
    r.rpush('weather_reports', str(data))
