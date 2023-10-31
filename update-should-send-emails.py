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


r = redis.Redis('localhost', 6379, charset="utf-8", decode_responses=True)
success = False

try:
    success, response = send_request()
    new_alarm_state = '1' if (success and response == 'yes') else '0'
    alarm_state_from_server = r.get('alarm_state_from_server')

    if alarm_state_from_server != new_alarm_state:
        r.set('alarm_state_from_server', new_alarm_state)
        r.set('alarm_state', new_alarm_state)
except BaseException as e:
    print("Error: %s" % str(e))

if not success:
    print('Failed to get get_should_send_emails from Google App Script')
