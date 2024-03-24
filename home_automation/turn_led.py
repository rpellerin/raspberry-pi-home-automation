import RPi.GPIO as GPIO
import sys
import logging

format_logs = "%(asctime)s: %(message)s"
logging.basicConfig(stream=sys.stdout, format=format_logs, level=logging.INFO)

GPIO.setmode(GPIO.BCM)


def turn_off():
    # GPIO.setwarnings(False)
    GPIO.setup(23, GPIO.OUT)  # 8th PIN on the external ROW of GPIO pins
    GPIO.output(23, GPIO.LOW)
    logging.info("LED off")


def turn_on():
    GPIO.setup(23, GPIO.OUT)  # 8th PIN on the external ROW of GPIO pins
    GPIO.output(23, GPIO.HIGH)
    logging.info("LED on")


def cleanup():
    GPIO.cleanup()
    logging.info("LED cleaned up")
