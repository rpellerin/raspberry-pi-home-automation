import requests
import redis
import importlib

# HOW TO USE:
# */5 * * * * /path/to/raspberry-pi-home-automation/.env/bin/python /path/to/raspberry-pi-home-automation/update-should-send-emails.py

config = importlib.import_module('config').get_config()

url=config.get('weatherstation', 'GOOGLE_SCRIPTS_WEATHER_URL')

def send_request():
    try:
        response = requests.get(url, params={ "get_should_send_emails": '1' })
        return (response.status_code == 200, response.text)
    except requests.exceptions.RequestException:
        return None


r = redis.Redis()
success = False

try:
    success, response = send_request()
    r.set('should_send_emails', '1' if (success and response == 'yes') else '0')
except BaseException as e:
    print("Error: %s" % str(e))

if not success:
    print('Failed to get get_should_send_emails from Google App Script')
