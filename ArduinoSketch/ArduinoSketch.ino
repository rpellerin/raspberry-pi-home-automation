#include <RCSwitch.h>

// To deploy:
// arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi path/to/raspberry-pi-home-automation/ArduinoSketch/
// arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:renesas_uno:unor4wifi path/to/raspberry-pi-home-automation/ArduinoSketch/
// To monitor: arduino-cli monitor -p /dev/ttyACM0. This will interrupt the connection any other process might have
// with the Arduino (door-sensor.py for instance).

RCSwitch mySwitch = RCSwitch();

// The RF receiver must be connected from VCC to 5V, GND to GND, and any of the two remaining pins to pin #2 on the Arduino, the 4th pin being useless.
// The PIR sensor must be connected from VCC to 5V, GND to GND, D1 to pin #3 on the Arduino, the 4th pin being useless.

#define RF_RECEIVER 2
#define PIR_MOTION_SENSOR 3
#define BUZZER 4

#define ON_SIGNAL ---REPLACE_ME---
#define OFF_SIGNAL ---REPLACE_ME---

void setup() {
  Serial.begin(9600); // To enable writing logs. As a side effect, this allows communication with the Raspberry Pi.
  mySwitch.enableReceive(RF_RECEIVER);
  pinMode(PIR_MOTION_SENSOR, INPUT);
  pinMode(BUZZER, OUTPUT);
}

void playOnSound() {
  digitalWrite(BUZZER, HIGH); // digitalWrite() for active buzzers, tone() for passive ones
  delay(100);
  digitalWrite(BUZZER, LOW);
  delay(100);
  digitalWrite(BUZZER, HIGH);
  delay(100);
  digitalWrite(BUZZER, LOW);
}

void playOffSound() {
  digitalWrite(BUZZER, HIGH);
  delay(300);
  digitalWrite(BUZZER, LOW);
}

// We do not want to systematically send detected motion to the Raspberry Pi, when the alarm is disengaged, because
// otherwise we would send too many "Motion detected" events to the Raspberry Pi, and the Pi would take time to process
// them all, delaying the processing of other events such as "ON pressed" or "OFF pressed".
bool shouldReportDetectedMotion = true;

void readInputFromRaspberryPi() {
  if (Serial.available() > 0) {
    String data = Serial.readStringUntil('\n');

    if (data == "play_on_sound") {
      playOnSound();
    }
    if (data == "disarm_alarm") {
      playOffSound();
      shouldReportDetectedMotion = false;
    }
    if (data == "arm_alarm") {
      shouldReportDetectedMotion = true;
    }
  }
}

void loop() {
  readInputFromRaspberryPi();

  if (mySwitch.available()) { // If we received a RF signal
    int value = mySwitch.getReceivedValue();

    if (value == ON_SIGNAL) {
      Serial.println("ON pressed");
    }
    else if (value == OFF_SIGNAL) {
      Serial.println("OFF pressed");
    }
    else {
      Serial.println("Unknown message received: " + String(value));
    }

    mySwitch.resetAvailable();
  }
  else {
    // Serial.println("No message received");
  }

  if (digitalRead(PIR_MOTION_SENSOR) && shouldReportDetectedMotion) {
    Serial.println("Motion detected");
  }
  else {
    // Serial.println("No motion");
  }

  delay(50);
}
