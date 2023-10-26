#include <RCSwitch.h>

RCSwitch mySwitch = RCSwitch();

// The RF receiver must be connected from VCC to 5V, GND to GND, and any of the two remaining pins to pin #2 on the Arduino, the 4th pin being useless.
// The PIR sensor must be connected from VCC to 5V, GND to GND, D1 to pin #3 on the Arduino, the 4th pin being useless.

#define RF_RECEIVER 2
#define PIR_MOTION_SENSOR 3

#define ON_SIGNAL 123
#define OFF_SIGNAL 321

void setup() {
  Serial.begin(9600); // To enable writing logs
  mySwitch.enableReceive(RF_RECEIVER);
  pinMode(PIR_MOTION_SENSOR, INPUT);
}

void loop() {
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

  if (digitalRead(PIR_MOTION_SENSOR)) {
    Serial.println("Motion detected");
  }
  else {
    // Serial.println("No motion");
  }

  delay(50);
}
