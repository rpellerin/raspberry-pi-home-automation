import smbus2
import bme280
import time
import requests
import redis
import json
import sys
from .config import GOOGLE_SCRIPTS_URL

port = 1
address = 0x76
bus = smbus2.SMBus(port)
now = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())

calibration_params = bme280.load_calibration_params(bus, address)


def send_request(data):
    try:
        response = requests.get(
            GOOGLE_SCRIPTS_URL,
            params={
                "datetime": data["timestamp"],
                "temperature": data["temperature"],
                "humidity": data["humidity"],
                "pressure": data["pressure"],
            },
        )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def send_report():
    raw_data = bme280.sample(bus, address, calibration_params)
    data = {
        "timestamp": now,
        "temperature": raw_data.temperature,
        "humidity": raw_data.humidity,
        "pressure": raw_data.pressure,
    }

    r = redis.Redis()
    r.lpush("weather_reports", json.dumps(data))
    r.ltrim("weather_reports", 0, 9999)  # No more than 10,000 elements stored in Redis

    successfully_sent = False

    try:
        successfully_sent = send_request(data)
    except BaseException as e:
        print("Error: %s" % str(e), file=sys.stderr)
    finally:
        if not successfully_sent:
            print("Failed to post to Google App Script", file=sys.stderr)
            print(data, file=sys.stderr)
        return successfully_sent
