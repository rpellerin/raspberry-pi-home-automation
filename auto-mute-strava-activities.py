import requests
import os
import sys
import json
import time
import redis
import threading
from geopy import distance
from http.server import HTTPServer, SimpleHTTPRequestHandler

# HOW TO USE:
# 0 */1 * * * DRY_RUN=0 COMMUTE_IF_CLOSE_TO="40.987,20.123" CLIENT_ID=123 CLIENT_SECRET="abc456" REFRESH_TOKEN=xyz /path/to/raspberry-pi-home-automation/.env/bin/python /path/to/raspberry-pi-home-automation/auto-mute-strava-activities.py

# A token can be obtained by running this script without the `REFRESH_TOKEN`` env variable.
REFRESH_TOKEN = os.getenv('REFRESH_TOKEN')
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
COMMUTE_IF_CLOSE_TO = os.environ.get('COMMUTE_IF_CLOSE_TO')
DRY_RUN = bool(int(os.environ.get('DRY_RUN') or "1"))

if (CLIENT_ID == None) or (CLIENT_SECRET == None):
    print('Please set CLIENT_ID and CLIENT_SECRET')
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

if (REFRESH_TOKEN == None):
    server = StoppableHTTPServer(('localhost', 8080), SimpleHTTPRequestHandler)
    t = threading.Thread(target=server.run)
    t.start()
    print(f'Now visit https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri=http://localhost:8080/strava-logger.html%3Fclient_creds%3D{CLIENT_ID}_{CLIENT_SECRET}&approval_prompt=auto&scope=read,activity:read_all,activity:write')
    try:
        input('Hit Enter when done\n')
    except KeyboardInterrupt:
        server.shutdown()
        print('Exiting')
        t.join()
        sys.exit(1)

    server.shutdown()
    t.join()
    print('Now you know your refresh token. Relaunch this script with REFRESH_TOKEN=xyz as an env variable.')
    sys.exit(0)

epoch_time             = int(time.time())
epoch_time_one_week_ago = epoch_time - (3600 * 24 * 7)

auth_url       = 'https://www.strava.com/api/v3/oauth/token'
activities_url = f'https://www.strava.com/api/v3/athlete/activities?per_page=100&after={epoch_time_one_week_ago}'

json_headers = {"Content-Type": "application/json"}

REDIS_INSTANCE = redis.Redis('localhost', 6379, charset="utf-8", decode_responses=True)

SAVED_REFRESH_TOKEN = REDIS_INSTANCE.get(REFRESH_TOKEN)

auth_payload = {
        'refresh_token': (SAVED_REFRESH_TOKEN or REFRESH_TOKEN),
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': "refresh_token",
      }

r = requests.post(auth_url, headers=json_headers, data=json.dumps(auth_payload))
r.raise_for_status()
response = json.loads(r.text)
ACCESS_TOKEN = response['access_token']
RECEIVED_REFRESH_TOKEN = response['refresh_token']

REDIS_INSTANCE.set(REFRESH_TOKEN, RECEIVED_REFRESH_TOKEN)

authenticated_headers = json_headers | { 'Authorization': f'Bearer {ACCESS_TOKEN}' }

r = requests.get(activities_url, headers=authenticated_headers)
r.raise_for_status()
activities = json.loads(r.text)

def was_not_yet_processed(activity):
    activity_id = activity["id"]

    if (REDIS_INSTANCE.get(f'strava_activity_{activity_id}') != None):
        print(f'Skipping activity {activity_id} as it was already processed')
        return False

    return True

def should_be_muted(activity):
    sport_type = activity['sport_type']
    distance = activity['distance']
    hide_from_home = ('hide_from_home' in activity) and (activity['hide_from_home'])
    # at the moment, `hide_from_home` is never present, even when true, while the doc says it should be there...

    return ((sport_type == "Walk") or (sport_type == "Ride" and distance < 10_000.0)) and (not hide_from_home)

MAXIMUM_DISTANCE_IN_KM = 0.5
OFFICE_POINT = (COMMUTE_IF_CLOSE_TO != None) and tuple([float(s.strip()) for s in COMMUTE_IF_CLOSE_TO.split(',')])

def is_close_to_office(activity):
    activity_start_point = tuple(activity['start_latlng'])
    activity_end_point = tuple(activity['end_latlng'])

    kms_to_start_point = distance.distance(OFFICE_POINT, activity_start_point).km
    kms_to_end_point = distance.distance(OFFICE_POINT, activity_end_point).km

    return (kms_to_start_point <= MAXIMUM_DISTANCE_IN_KM) or (kms_to_end_point <= MAXIMUM_DISTANCE_IN_KM)

def should_be_marked_as_commute(activity):
    if COMMUTE_IF_CLOSE_TO == None:
        print(f"COMMUTE_IF_CLOSE_TO not provided, cannot evaluate activity {activity['id']}")
        return False

    sport_type = activity['sport_type']
    distance = activity['distance']

    return (sport_type == "Ride" and distance < 10_000.0) and (is_close_to_office(activity))


# sport_type, distance, hide_from_home
print(f'Received in total {len(activities)} activities')
activities_non_processed = list(filter(was_not_yet_processed, activities))

activites_to_mute = list(filter(should_be_muted, activities_non_processed))
activites_to_mark_as_commute = list(filter(should_be_marked_as_commute, activities_non_processed))

EXPIRATION_IN_ONE_YEAR = 60 * 60 * 24 * 365

def process_activities(activities, payload, log_message):
    for i, activity in enumerate(activities):
        activity_id = activity["id"]
        print(f'{i+1:02d}/{len(activities)}: https://www.strava.com/activities/{activity_id} marked as {log_message}')

        if not DRY_RUN:
            activity_url = f'https://www.strava.com/api/v3/activities/{activity_id}'
            r = requests.put(activity_url, headers=authenticated_headers, data=json.dumps(payload))
            r.raise_for_status()
            REDIS_INSTANCE.set(f'strava_activity_{activity_id}', 1, EXPIRATION_IN_ONE_YEAR)
            print(f'Marked https://www.strava.com/activities/{activity_id} as processed')
        else:
            print('Dry run. No effect.')

process_activities(activites_to_mute, { 'hide_from_home': True }, "hidden")
process_activities(activites_to_mark_as_commute, { 'commute': True }, "commute")
