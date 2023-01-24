#!/bin/bash -ex

filename="$(date +"%Y-%m-%dT%H-%M-%SZ")"
#raspistill -q 100 -rot 180 -n -co 10 -o "/tmp/$filename.jpg"
raspivid -a 12 -w 1296 -h 972 -hf -vf -fps 25 -t 15000 -b 3000000 -o "/tmp/$filename.h264" # 300k bytes per second
ffmpeg -r 25 -i "/tmp/$filename.h264" -vcodec copy "/tmp/$filename.mp4"
echo "On `date`" | mail -s "Door opened" -A "/tmp/$filename.mp4" root@localhost
