# Setting up the Raspberry Pi

Follow [a tutorial I have written](https://romainpellerin.eu/raspberry-pi-the-ultimate-guide.html) to set up the Pi. Do not set `max_usb_current=1` if the power supply cannot output more than 1A. When running `raspi-config`, make sure to:

- Enable the camera. First make sure it works by running `libcamera-still -o test.jpg`.
- Give the GPU at least 128MB (more is recommended, apparently)

You can stop reading the tutorial at the end of the section "Configuration".

## Fine tuning wthen using a SD card only (no external SDD)

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

Head over to [the `temperature/` folder](temperature/README.md).

# Security camera (CCTV)

Now has come the time to turn off the Raspberry Pi, unplug the power supply, ground yourself, and plug in the camera model in the CSI port (next to the HDMI one). The camera module is very vulnerable to static eletrictiy that's why we have to be that cautious.

Then turn it back on and make sure it is correctly detected:

```bash
sudo vcgencmd get_camera
```

To adjust the focus, rotate the lens (when facing it) clockwise to focus on distant objects.

## Software for motion detection and video/image capture

Now, we've got two options.

1.  Build our own solution based on [Python scripts](https://picamera.readthedocs.io/). Tedious and far from perfect.
2.  Use an existing software program. Seems to be the best solution.

There are plenty of existing programs to do motion detection on a Raspberry Pi. The two most interesting ones I found are these two:

- [Motion](https://github.com/Motion-Project/motion/)
- [Raspberry PI-TIMOLO](https://github.com/pageauc/pi-timolo)

The first one seems to be quite a big project, with a large community. On the other hand, the second one is more of a personal side-project and seems to be lacking features Motion has. So I decided to give Motion a try.

Also note that Motion comes with a web frontend, [MotionEye](https://github.com/ccrisan/motioneye). Since our camera has no motor to rotate, I thought there was no need for a web interface with controls. If there ever was to be motion, I would get emails with pictures anyway. Therefore I did not install MotionEye.

## Motion

### Install

Although installation through `apt` is possible, you will most likely get an outdated version of Motion. I decided to build it from their Github repo. [Here is the official turorial I followed](https://motion-project.github.io/motion_build.html#BUILD_DEBIAN). Make sure to also install `ffmpeg` with `apt` (only useful to make videos out of pictures though, but you'll probaly want to try this feature out).

We want Motion to be able to send emails, so let's install Exim4 by reading the relevant section on [my tutorial here]({filename}/raspberry-pi-the-ultimate-guide.md). Or you might want to use a simpler solution with [`mpack`](https://www.bouvet.no/bouvet-deler/utbrudd/building-a-motion-activated-security-camera-with-the-raspberry-pi-zero).

The configuration file I personally use when running Motion (`motion -c motion-dist.conf`) is here in this very repository.

# Meeting the [initial requirements](MOTIVATION.md)

Now that we just installed Motion, let's address the above-mentioned requirements one by one.

## Basic features

- _Must send good resolution pictures (and videos if need be) on motion detection_

  > This is addressed in the configuration file above.

- _Must be easily concealable (no LEDs visible, even at night)_

  > Do your best to do this with duck tape, Blu Tack or something else.

- _Must be easily turned on and started_

  > I connected my Raspberry with an extension cord that has a switch. As to the auto start feature, here is how to do it:

First, copy the SystemD file and enable the service:

```bash
sudo cp motion/data/motion.service /etc/systemd/system/
sudo systemctl enable motion.service
```

Add these two lines below `[Service]` and edit the third line:

```text
Restart=always
RestartSec=3
ExecStart=/usr/local/bin/motion -n -c /home/pi/raspberry-pi-home-automation/motion-dist.conf
```

Replace the existing line `ExecStart` with the one above. `-n` is to force non-daemon mode.

Then run:

```bash
sudo systemctl daemon-reload
sudo systemctl start motion
sudo systemctl status motion
```

If that does not work, use the file `services/motion.service` from this repository, after cloning this repository in your home folder.

- _Must be able to live stream to the Internet if I want to_

  > Addressed in the configuration file above. Make sure to open ports to the Internet in your router configuration.

## Advanced features (from most important to least)

- _Must no fail because of the SD card_

  > This one can be addressed by using an [external HDD](https://www.kubii.fr/carte-sd-et-stockage/1790-disque-dur-pidrive-foundation-edition-kubii-718037846736.html) for the root partition instead of a SD card.

- _Not easily hackable (penetrable) through my LAN or the Internet_

  > Quite simple. Disable Wifi when the security camera is on. Also, don't expose it to the Internet (don't allow ports to be reached through your router). This disables live streaming but strengthens security.

- _Must send daily signs of life as a proof no one took it down on purpose or my apartment did not burn down_

  > For this one, we are going to create a cron that runs daily and send an email. See bullet point below.

- _Must free up space when it runs out of disk space_

  > A good solution would be to create a script that runs every 30mins thanks to cron, check for space left. If too little, it zips all the pictures and videos just in case you did not get them, email it to you and then delete the zip and the original files. Please see the file `alive-script.sh` in this repository. Then run `crontab -e` as `pi` and:

```bash
# Sends out an email saying hi and returns
0    12 * * * /home/pi/raspberry-pi-home-automation/alive-script.sh --daily
# Checks for remaining space left, delete pics and vids if necessary
*/30 *  * * * /home/pi/raspberry-pi-home-automation/alive-script.sh
# Deletes all pics and vids created more than 30 days ago
0 11 * * * find /home/pi/pics_and_vids/ -type f -mtime +30 -exec rm '{}' \;
```

- _Must notify me when being turned on and tell me how long it had been off_

  > Shoud be easy.

Add the following in /etc/rc.local, right above `exit 0`:

```bash
echo "So you know... ($(date))" | mail -s "Rpi turned on" root &
sleep 2
echo -e "So you know... ($(date))\n\n$(tail -n 500 /var/log/syslog)" | mail -s "Rpi turned on (with syslog)" root &
sleep 15
exit 0
```

An alternative is to add a cronjob that runs at every reboot, sleeps for two minutes (in case network is not immediately available) and sends an email. See `boot-email.sh`. Then:

```bash
chmod +x boot-email.sh
sudo su
crontab -e
@reboot /home/pi/raspberry-pi-home-automation/boot-email.sh
```

- _Must be resiliant to power outage, and auto-restart. Must also handle cases when network is not available_

  > Auto start was addressed a few lines above. However, how to wait for network to be up? [TODO](https://www.raspberrypi.org/forums/viewtopic.php?t=187225) and [TODO](https://www.raspberrypi.org/forums/viewtopic.php?p=1054207#p1054207).

- _Must notify me when being purposedly shut down_

  > [This question on StackOverflow](https://unix.stackexchange.com/questions/39226/how-to-run-a-script-with-systemd-right-before-shutdown) and [this tutorial](https://opensource.com/life/16/11/running-commands-shutdown-linux) should help though.

- _Must be easily shut down when I get home (through a physical button ideally)_

  > I bought a [switch cable from Amazon](http://a.co/d/2TyyK1D), connected it to the pins 5 and 6 (GROUND and GPIO 3) and followed this [tutorial](https://github.com/TonyLHansen/raspberry-pi-safe-off-switch/):

```bash
sudo apt install python3-gpiozero redis-server python3-picamera ffmpeg
python3 -m venv .env
source .env/bin/activate
pip3 install -r requirements.txt
sudo cp services/shutdown.service services/door-sensor.service /etc/systemd/system
sudo systemctl enable shutdown.service
sudo systemctl enable door-sensor.service
sudo systemctl daemon-reload
sudo systemctl start shutdown.service
sudo systemctl start door-sensor.service
```

- _Must detect when no connectivity and be resiliant to it_

  > Yet to do...

- _Must notify me when someone logs in to the Raspberry Pi, either remotely or physically with a keyboard connected to it_

  > Yet to do...

Hope this helps.

# Further reading

- [Smarten up your Pi Zero Web Camera with Image Analysis and Amazon Web Services (Part 1)](https://www.bouvet.no/bouvet-deler/utbrudd/smarten-up-your-pi-zero-web-camera-with-image-analysis-and-amazon-web-services-part-1)
- [Limit the runtime of a cronjob or script](https://ma.ttias.be/limit-runtime-cronjob-script/)
- [A Guide to Recording 660FPS Video On A $6 Raspberry Pi Camera](http://blog.robertelder.org/recording-660-fps-on-raspberry-pi-camera/)
