import requests
import importlib
import os

# HOW TO USE:
# */6 * * * * /path/to/raspberry-pi-home-automation/.venv/bin/python /path/to/raspberry-pi-home-automation/update-should-reboot.py

config = importlib.import_module("config").get_config()

url = config.get("weatherstation", "GOOGLE_SCRIPTS_WEATHER_URL")


def send_request():
    try:
        response = requests.get(url, params={"get_should_reboot": "1"})
        return (response.status_code == 200, response.text)
    except requests.exceptions.RequestException:
        return None


success = False

try:
    success, response = send_request()
    should_reboot = True if (success and response == "yes") else False

    if should_reboot:
        os.system(
            f'echo "As requested." | mail -s "Raspberry is rebooting." root@localhost'
        )
        os.system("sudo reboot")
except BaseException as e:
    print("Error: %s" % str(e))

if not success:
    print("Failed to get get_should_reboot from Google App Script")
