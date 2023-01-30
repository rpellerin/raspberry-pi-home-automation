#!/bin/bash -ex

filename="$(date +"%Y-%m-%dT%H-%M-%SZ")"

# Legacy as of 2022
raspivid -a 12 -w 1296 -h 972 -hf -vf -fps 25 -t 15000 -b 3000000 -o "/tmp/$filename.h264" # 3000k bits per second (300kB/s)

# New way of recording
#libcamera-vid --width 1296 --height 972 --hflip --vflip --framerate 25 -t 15000 -b 3000000 -o "/tmp/$filename.h264" # 3000k bits per second (300kB/s)

ffmpeg -r 25 -i "/tmp/$filename.h264" -vcodec copy "/tmp/$filename.mp4"
echo "On `date`" | mail -s "Door opened" -A "/tmp/$filename.mp4" root@localhost
