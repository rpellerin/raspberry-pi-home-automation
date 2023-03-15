#!/bin/bash -ex

#echo "On `date`" | mail -s "Door just opened" root@localhost
filename="$(date +"%Y-%m-%dT%H-%M-%SZ")"

/home/pi/raspberry-pi-home-automation/.env/bin/python /home/pi/raspberry-pi-home-automation/turn-led-on.py &

libcamera-vid -t 20000 --width 1296 --height 972 --framerate 25 - b 3000000 --rotation 180 -o "/tmp/$filename.h264" --save-pts "/tmp/$filename-timestamps.txt" # 3000k bits per second (300kB/s)

/home/pi/raspberry-pi-home-automation/.env/bin/python /home/pi/raspberry-pi-home-automation/turn-led-off.py

sync
#ffmpeg -r 25 -i "/tmp/$filename.h264" -vcodec copy "/tmp/$filename.mp4"
mkvmerge -o "/tmp/$filename.mkv" --timecodes "0:/tmp/$filename-timestamps.txt" "/tmp/$filename.h264"
sync
echo "On `date`" | mail -s "Door opened" -A "/tmp/$filename.mkv" root@localhost
