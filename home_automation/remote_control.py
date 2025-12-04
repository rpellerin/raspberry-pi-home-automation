import requests
import redis
import importlib
import json
import sys
import os
from .config import GOOGLE_SCRIPTS_URL


def send_request(current_value):
    try:
        response = requests.get(
            GOOGLE_SCRIPTS_URL, params={"remote_control": current_value}
        )
        return (response.status_code == 200, json.loads(response.text))
    except requests.exceptions.RequestException:
        return None


def update_alarm_state(should_enable_alarm, current_alarm_state, r):
    new_alarm_state = current_alarm_state
    if should_enable_alarm == "yes":
        new_alarm_state = "1"
    elif should_enable_alarm == "no":
        new_alarm_state = "0"

    if new_alarm_state != current_alarm_state:
        r.set("alarm_state", new_alarm_state)
        # We need to update the value in the sheet again, to reflect the change of state
        send_request("yes" if new_alarm_state == "1" else "no")


def initiate_reboot():
    os.system(f'echo "As requested." | mail -s "Raspberry is rebooting" root@localhost')
    os.system("sudo reboot")


def run():
    r = redis.Redis("localhost", 6379, charset="utf-8", decode_responses=True)
    success = False

    try:
        alarm_state = r.get("alarm_state")
        success, response = send_request("yes" if alarm_state == "1" else "no")

        if success:
            should_enable_alarm = response["shouldEnableAlarm"]
            should_reboot = response["shouldReboot"]

            if should_enable_alarm != "":
                update_alarm_state(should_enable_alarm, alarm_state, r)

            if should_reboot == "yes":
                initiate_reboot()
    except BaseException as e:
        print("Error: %s" % str(e))
        print(e)
        success = False

    if not success:
        print("Failed to fetch 'remote_control' from App Script", file=sys.stderr)

    return success
