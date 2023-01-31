I have owned for a long time a [Heden IP security camera](http://www.heden.fr/55-18-Cameras-de-surveillance-Camera-Int-Motorisee-p-247-Camera-IP-Interieure---Wifi---V-5.5---Noir.html). I had been very content with it until the moment it stopped sending emails, for no reason. It was still working though, I could access a live stream from the Internet, but it just would not send emails. Therefore, I decided it was time to build something by myself with a Raspberry Pi. The only thing that was cool about my old security camera - but I won't miss - was its ability to rotate and be remotely controlled, so that I could have a pretty large view of my apartment. But I wasn't making any use of it since I was not actively watching the live stream. I was however using the email on alert feature.

# Requirements for my new project

Let's start off with listing the requirements for this project.

## Basic features

- Must send good resolution pictures (and videos if need be) on motion detection
- Must be easily concealable (no LEDs visible, even at night)
- Must be easily turned on
- Must be able to live stream to the Internet if I want to

## Advanced features (from most important to least)

- Must not fail because of the SD card
- Not easily hackable (penetrable) through my LAN
- Must send daily signs of life as a proof no one took it down on purpose or my apartment did not burn down
- Must free up space when it runs out of disk space
- Must notify me when being turned on and tell me how long it had been off
- Must be resiliant to power outage, and auto-restart. Must also handle cases when network is not available
- Must notify me when being purposedly shut down
- Must be easily shut down when I get home (through a physical button ideally)
- Must detect when no connectivity and be resiliant to it
- Must notify me when someone logs in to the Raspberry Pi, either remotely or physically with a keyboard connected to it

Now let's try to address these bullet points one by one. But first, the big picture.

# Hardware

For this project, I used an old Rasberry Pi 1 model B revision 2, an Ethernet cable and the [camera module version 2.1](https://www.kubii.fr/cameras-accessoires/1653-module-camera-v2-8mp-kubii-640522710881.html). You should consider buying the Pi NoIR camera with infrared LEDs to enable night vision (daylight pictures however look red-ish and bad quality).
