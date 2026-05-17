import requests
import redis
import json
import sys
import os
from .config import GOOGLE_SCRIPTS_URL


def report_alarm_status_and_fetch_sheet_data(*, is_alarm_enabled):
    """
    Sends the current alarm status to the Google Script and fetches the desired state from the sheet
    (force reboot and force enable alarm)

    :param is_alarm_enabled: The current status of the alarm ("yes" for enabled, "no" for disabled).
    :return: A tuple containing (success: bool, response_data: dict|None).
    """
    try:
        response = requests.get(
            GOOGLE_SCRIPTS_URL,
            params={"remote_control": is_alarm_enabled},
            timeout=20,
        )
        return (response.status_code == 200, json.loads(response.text))
    except requests.exceptions.RequestException as e:
        # Would be logged to `journalctl -u cron.service`
        print(f"RequestException occurred: {e}", file=sys.stderr)
        return (False, None)


def update_alarm_state(*, should_enable_alarm, current_alarm_state, redis):
    new_alarm_state = current_alarm_state
    if should_enable_alarm == "yes":
        new_alarm_state = "1"
    elif should_enable_alarm == "no":
        new_alarm_state = "0"

    if new_alarm_state != current_alarm_state:
        redis.set("alarm_state", new_alarm_state)
        # We need to update the value in the sheet again, to reflect the change of state
        success, response = report_alarm_status_and_fetch_sheet_data(is_alarm_enabled="yes" if new_alarm_state == "1" else "no")
        if not success:
            print(f"Could not push change of alarm state to the sheet (new state: {new_alarm_state})", file=sys.stderr)


def initiate_reboot():
    os.system(f'echo "As requested on $(/bin/date)." | mail -s "Raspberry is rebooting" root@localhost')
    os.system("sudo reboot")


def run():
    redis_instance = redis.Redis("localhost", 6379, charset="utf-8", decode_responses=True)
    success = False

    try:
        alarm_state = redis_instance.get("alarm_state")
        success, response = report_alarm_status_and_fetch_sheet_data(is_alarm_enabled="yes" if alarm_state == "1" else "no")

        if success:
            should_enable_alarm = response["shouldEnableAlarm"]
            should_reboot = response["shouldReboot"]

            if should_enable_alarm != "":
                update_alarm_state(
                    should_enable_alarm=should_enable_alarm,
                    current_alarm_state=alarm_state,
                    redis=redis_instance
                )

            if should_reboot == "yes":
                initiate_reboot()
        else:
            print("Error when fetching sheet data", file=sys.stderr)
    except BaseException as e:
        print("Error: %s" % str(e), file=sys.stderr)
        print(e)
        success = False

    if not success:
        # Would be logged to `journalctl -u cron.service`
        print("Failed to fetch 'remote_control' from App Script", file=sys.stderr)

    return success
