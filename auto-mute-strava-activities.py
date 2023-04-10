import requests
import os
import sys
import json
import time

# A token can be obtained by running this https://github.com/rpellerin/commute-auto-tagger/ with the credentials of
# a Strava App, and logging in. Then, window.localStorage.getItem("refreshToken")
REFRESH_TOKEN = os.getenv('REFRESH_TOKEN')
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')

if (REFRESH_TOKEN == None) or () or ():
    print('Please set REFRESH_TOKEN, CLIENT_ID and CLIENT_SECRET')
    sys.exit(1)

epoch_time             = int(time.time())
epoch_time_one_week_ago = epoch_time - (3600 * 24 * 7)

auth_url       = 'https://www.strava.com/api/v3/oauth/token'
activities_url = f'https://www.strava.com/api/v3/athlete/activities?per_page=100&after={epoch_time_one_week_ago}'

json_headers = {"Content-Type": "application/json"}

auth_payload = {
        'refresh_token': REFRESH_TOKEN,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': "refresh_token",
      }

r = requests.post(auth_url, headers=json_headers, data=json.dumps(auth_payload))
r.raise_for_status()
ACCESS_TOKEN = json.loads(r.text)['access_token']

authenticated_headers = json_headers | { 'Authorization': f'Bearer {ACCESS_TOKEN}' }

r = requests.get(activities_url, headers=authenticated_headers)
r.raise_for_status()
activities = json.loads(r.text)

def should_be_muted(activity):
    sport_type = activity['sport_type']
    distance = activity['distance']
    hide_from_home = ('hide_from_home' in activity) and (activity['hide_from_home'])
    # at the moment, `hide_from_home` is never present, even when true, while the doc says it should be there...

    return ((sport_type == "Walk") or (sport_type == "Ride" and distance < 10_000.0)) and (not hide_from_home)

# sport_type, distance, hide_from_home
print(f'Received in total {len(activities)} activities')
activites_to_mute = list(filter(should_be_muted, activities))

for i, activity in enumerate(activites_to_mute):
    print(f'Mutting {i+1:02d}/{len(activites_to_mute)} https://www.strava.com/activities/{activity["id"]}')
    payload = { 'hide_from_home': True }
    activity_url = f'https://www.strava.com/api/v3/activities/{activity["id"]}'
    r = requests.put(activity_url, headers=authenticated_headers, data=json.dumps(payload))
    r.raise_for_status()
