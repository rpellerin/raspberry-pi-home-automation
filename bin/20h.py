#!/bin/env -S sh -c '"`dirname $0`/../.venv/bin/python3" "$0" "$@"'

# This script can be invoked in two different ways with the same result:
# $ /path/to/raspberry-pi-home-automation/bin/20h.py (thanks to the complex shebang above)
# $ /path/to/raspberry-pi-home-automation/.venv/bin/python3 /path/to/raspberry-pi-home-automation/bin/20h.py

import requests
import re
import yt_dlp
from bs4 import BeautifulSoup

# crontab -e
# 08 21 * * * /path/to/raspberry-pi-home-automation/.venv/bin/python3 -m pip install -U --pre "yt-dlp[default]"
# 10 21 * * * /path/to/raspberry-pi-home-automation/bin/20h.py

url = "https://www.france.tv/france-2/journal-20h00/"

if __name__ == '__main__':
    html_text = requests.get(url).text
    soup = BeautifulSoup(html_text, "html.parser")
    latest_video = soup.select_one("main #les-editions ul li:first-child a")

    if latest_video != None:
        video_url = re.sub(r"^/", "https://www.france.tv/", latest_video["href"])
        print("Downloading " + video_url)
        with yt_dlp.YoutubeDL(
            {
                "outtmpl": {
                    "default": "/var/lib/minidlna/20h-%(upload_date>%Y-%m-%d)s.%(ext)s"
                }
            }
        ) as ydl:
            ydl.download([video_url])
