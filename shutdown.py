#!/usr/bin/env python3

# Inspired from: https://github.com/TonyLHansen/raspberry-pi-safe-off-switch/

from gpiozero import Button, LED
from signal import pause
import os, sys
import warnings

offGPIO = 3 # PIN 5
holdTime = 2
ledGPIO = 16 # On Rpi 1 model B

print('Starting shutdown.py...')

# Enable trigger by GPIO
# https://gpiozero.readthedocs.io/en/stable/recipes_advanced.html#controlling-the-pi-s-own-leds
def when_pressed():
    os.system('echo "Hello, friend." | mail -s "Raspberry Pi button pressed" root@localhost')
    led.blink(on_time=0.5, off_time=0.5)

def when_released():
    led.off()

def shutdown():
    print('Shutting down the Raspberry Pi...')
    os.system("poweroff")

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    # active_high=False is specific to Rpi 1 model B: it prevents from turning the LED on when executing this line
    led = LED(ledGPIO, active_high=False)

btn = Button(offGPIO, hold_time=holdTime)
btn.when_held = shutdown
btn.when_pressed = when_pressed
btn.when_released = when_released
pause() # Handles the button presses in the background
