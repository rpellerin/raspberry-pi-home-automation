# Setting up the Raspberry Pi

![GPIO pins](GPIO.png)

# Setup

After installing a fresh version of Raspbian, and cloning this repo, follow [the beginning of a tutorial I have written](https://romainpellerin.eu/raspberry-pi-the-ultimate-guide.html) to set up the Pi. Do not set `max_usb_current=1` if the power supply cannot output more than 1A. When running `raspi-config`, make sure to:

- Enable the camera. First make sure it works by running `libcamera-still -o test.jpg`.
- Give the GPU at least 128MB (more is recommended, apparently)

You can stop reading the tutorial at the end of the section "Configuration".

## Crontab

```bash
crontab -e
0 21 * * * find /var/lib/minidlna -type f -mtime +2 -exec rm '{}' \;
0 21 * * * find /tmp -type f -iname '*.mp4' -mtime +90 -exec rm '{}' \;
0 21 * * * find /tmp -type f -iname '*.h264' -mtime +90 -exec rm '{}' \;

sudo su
crontab -e
@reboot /bin/sleep 20; /usr/sbin/exim -qff; echo "So you know... ($(/bin/date))\n\n$(/usr/bin/tail -n 500 /var/log/syslog)" | mail -s "Rpi turned on 20secs ago" root
```

## Fine tuning when using a SD card only (no external SDD)

```bash
sudo tune2fs -c -1 -i 0 /dev/mmcblk0p2 # no check when booting
sudo tune2fs -O ^has_journal /dev/mmcblk0p2 # no journalling, must be done from a PC on mmcblk0p2 unmounted
```

In `/etc/fstab`:

```bash
/dev/mmcblk0p2 / ext4 defaults,noatime 0 0 # final zero means never run fsck
tmpfs /tmp tmpfs defaults,noatime,size=34m 0 0
tmpfs /var/log tmpfs defaults,noatime,size=30m 0 0
```

Also disable swaping to extend your SD card lifetime:

```bash
sudo swapoff --all # Temporary
sudo update-rc.d -f dphys-swapfile remove
sudo apt remove dphys-swapfile # Permanently
sudo rm /var/swap
```

# Temperature

Head over to [report_weather.README.md](report_weather.README.md).

# MiniDLNA

Head over to [the `minidlna/` folder](minidlna/README.md).

# Security camera (CCTV)

Make sure the camera is correctly detected:

```bash
sudo vcgencmd get_camera
```

## Setup

```bash
sudo apt install python3-gpiozero redis-server python3-picamera ffmpeg libatlas-base-dev python3-picamera2 python3-opencv

cd /to/the/cloned/repo

python3 -m venv --system-site-packages .env # --system-site-packages to have the system-installed picamera2 module available
source .env/bin/activate
pip3 install -r requirements.txt

sudo cp services/shutdown.service services/door-sensor.service services/video-recorder.service /etc/systemd/system

sudo systemctl enable shutdown.service
sudo systemctl enable door-sensor.service
sudo systemctl enable video-recorder.service
sudo systemctl daemon-reload
sudo systemctl start shutdown.service
sudo systemctl start door-sensor.service
sudo systemctl start video-recorder.service
```

# Further reading

- [Smarten up your Pi Zero Web Camera with Image Analysis and Amazon Web Services (Part 1)](https://www.bouvet.no/bouvet-deler/utbrudd/smarten-up-your-pi-zero-web-camera-with-image-analysis-and-amazon-web-services-part-1)
- [Limit the runtime of a cronjob or script](https://ma.ttias.be/limit-runtime-cronjob-script/)
- [A Guide to Recording 660FPS Video On A $6 Raspberry Pi Camera](http://blog.robertelder.org/recording-660-fps-on-raspberry-pi-camera/)
- [Xiaomi Miijia LYWSD03MMC with pure bluetoothctl](https://false.ekta.is/2021/06/xiaomi-miijia-lywsd03mmc-with-pure-bluetoothctl/)
- [Multiple cameras with the Raspberry Pi and OpenCV](https://pyimagesearch.com/2016/01/18/multiple-cameras-with-the-raspberry-pi-and-opencv/)
