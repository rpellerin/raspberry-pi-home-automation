#!/bin/env -S sh -c '"`dirname $0`/../.venv/bin/python3" "$0" "$@"'

# This script can be invoked in two different ways with the same result:
# $ /path/to/raspberry-pi-home-automation/bin/auto-mute-strava-activities.py (thanks to the complex shebang above)
# $ /path/to/raspberry-pi-home-automation/.venv/bin/python3 /path/to/raspberry-pi-home-automation/bin/auto-mute-strava-activities.py

import requests
import os
import sys
import json
import time
import redis
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

# HOW TO USE WITH CRON:
# 0 */1 * * * DRY_RUN=0 CLIENT_ID=123 CLIENT_SECRET="abc456" REFRESH_TOKEN=xyz /path/to/raspberry-pi-home-automation/bin/auto-mute-strava-activities.py

# A token can be obtained by running this script without the `REFRESH_TOKEN`` env variable.
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
DRY_RUN = bool(int(os.environ.get("DRY_RUN") or "1"))
DO_NOT_HIDE_RUNS = bool(int(os.environ.get("DO_NOT_HIDE_RUNS") or "0"))

if (CLIENT_ID == None) or (CLIENT_SECRET == None):
    print("Please set CLIENT_ID and CLIENT_SECRET")
    sys.exit(1)


class StoppableHTTPServer(HTTPServer):
    def run(self):
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            # Clean-up server (close socket, etc.)
            self.server_close()


if REFRESH_TOKEN == None:
    server = StoppableHTTPServer(("localhost", 8080), SimpleHTTPRequestHandler)
    t = threading.Thread(target=server.run)
    t.start()
    print(
        f"Now visit https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri=http://localhost:8080/strava-logger.html%3Fclient_creds%3D{CLIENT_ID}_{CLIENT_SECRET}&approval_prompt=auto&scope=read,activity:read_all,activity:write"
    )
    try:
        input("Hit Enter when done\n")
    except KeyboardInterrupt:
        server.shutdown()
        print("Exiting")
        t.join()
        sys.exit(1)

    server.shutdown()
    t.join()
    print(
        "Now you know your refresh token. Relaunch this script with REFRESH_TOKEN=xyz as an env variable."
    )
    sys.exit(0)

epoch_time = int(time.time())
epoch_time_one_week_ago = epoch_time - (3600 * 24 * 7)

auth_url = "https://www.strava.com/api/v3/oauth/token"
activities_url = f"https://www.strava.com/api/v3/athlete/activities?per_page=100&after={epoch_time_one_week_ago}"

json_headers = {"Content-Type": "application/json"}

REDIS_INSTANCE = redis.Redis("localhost", 6379, charset="utf-8", decode_responses=True)

SAVED_REFRESH_TOKEN = REDIS_INSTANCE.get(REFRESH_TOKEN)

auth_payload = {
    "refresh_token": (SAVED_REFRESH_TOKEN or REFRESH_TOKEN),
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "grant_type": "refresh_token",
}

r = requests.post(auth_url, headers=json_headers, data=json.dumps(auth_payload))
r.raise_for_status()
response = json.loads(r.text)
ACCESS_TOKEN = response["access_token"]
RECEIVED_REFRESH_TOKEN = response["refresh_token"]

REDIS_INSTANCE.set(REFRESH_TOKEN, RECEIVED_REFRESH_TOKEN)

authenticated_headers = json_headers | {"Authorization": f"Bearer {ACCESS_TOKEN}"}

r = requests.get(activities_url, headers=authenticated_headers)
r.raise_for_status()
activities = json.loads(r.text)


def was_not_yet_processed(activity):
    activity_id = activity["id"]

    if REDIS_INSTANCE.get(f"strava_activity_{activity_id}") != None:
        print(f"Skipping activity {activity_id} as it was already processed")
        return False

    return True


def should_be_muted(activity):
    sport_type = activity["sport_type"]
    distance = activity["distance"]
    hide_from_home = ("hide_from_home" in activity) and (activity["hide_from_home"])
    # at the moment, `hide_from_home` is never present, even when true, while the doc says it should be there...

    return (
        (sport_type == "Walk")
        or (sport_type == "Ride" and distance < 10_000.0)
        or ((not DO_NOT_HIDE_RUNS) and (sport_type == "Run" and distance < 15_000.0))
    ) and (not hide_from_home)


# sport_type, distance, hide_from_home
print(f"Received in total {len(activities)} activities")
activities_non_processed = list(filter(was_not_yet_processed, activities))

activites_to_mute = list(filter(should_be_muted, activities_non_processed))

EXPIRATION_IN_ONE_YEAR = 60 * 60 * 24 * 365


def process_activities(activities, payload, log_message):
    for i, activity in enumerate(activities):
        activity_id = activity["id"]
        print(
            f"{i+1:02d}/{len(activities)}: https://www.strava.com/activities/{activity_id} marked as {log_message}"
        )

        if not DRY_RUN:
            activity_url = f"https://www.strava.com/api/v3/activities/{activity_id}"
            r = requests.put(
                activity_url, headers=authenticated_headers, data=json.dumps(payload)
            )
            r.raise_for_status()
            REDIS_INSTANCE.set(
                f"strava_activity_{activity_id}", 1, EXPIRATION_IN_ONE_YEAR
            )
            print(
                f"Marked https://www.strava.com/activities/{activity_id} as processed"
            )
        else:
            print("Dry run. No effect.")


process_activities(activites_to_mute, {"hide_from_home": True}, "hidden")
