import pytest
import tempfile
from unittest.mock import patch, mock_open, ANY
from importlib import reload
import home_automation.build_arduino_sketch_and_deploy as build_arduino_sketch_and_deploy

mock_config_file_with_missing_values = """
[weatherstation]
GOOGLE_SCRIPTS_URL=https://some.url

[arduino]
RF_ON_SIGNAL=
RF_OFF_SIGNAL=
"""

mock_config_file = """
[weatherstation]
GOOGLE_SCRIPTS_URL=https://some.url

[arduino]
RF_ON_SIGNAL=123123
RF_OFF_SIGNAL=321321
"""


class MockOpenForConfigOnly:
    builtin_open = open

    def __init__(self, read_data):
        self.read_data = read_data

    def open(self, *args, **kwargs):
        if args[0].endswith("/config.txt"):
            return mock_open(read_data=self.read_data)(*args, **kwargs)
        return self.builtin_open(*args, **kwargs)


class TestBuildArduinoSketchAndDeploy:
    @patch("builtins.open", mock_open(read_data=""))
    def test_fails_without_any_configuration(self):
        reload(build_arduino_sketch_and_deploy)
        with pytest.raises(SystemExit):
            build_arduino_sketch_and_deploy.build_and_deploy()

    @patch("builtins.open", mock_open(read_data="[arduinooo]"))
    def test_fails_without_the_right_configuration(self):
        reload(build_arduino_sketch_and_deploy)
        with pytest.raises(SystemExit):
            build_arduino_sketch_and_deploy.build_and_deploy()

    @patch("builtins.open", mock_open(read_data=mock_config_file_with_missing_values))
    def test_fails_with_missing_values(self):
        reload(build_arduino_sketch_and_deploy)
        with pytest.raises(SystemExit):
            build_arduino_sketch_and_deploy.build_and_deploy()

    def test_destination_file_in_directory(self):
        with pytest.raises(ValueError):
            build_arduino_sketch_and_deploy.destination_file_in_directory()

        assert (
            "/tmp/yolo/yolo.ino"
            == build_arduino_sketch_and_deploy.destination_file_in_directory(
                "/tmp/yolo"
            )
        )

    @patch("builtins.open", MockOpenForConfigOnly(read_data=mock_config_file).open)
    def test_replace_in_file(self):
        reload(build_arduino_sketch_and_deploy)
        with tempfile.TemporaryDirectory() as destination_directory, open(
            build_arduino_sketch_and_deploy.destination_file_in_directory(
                destination_directory
            ),
            "x",
        ) as destination_file:
            build_arduino_sketch_and_deploy.replace_in_file(
                build_arduino_sketch_and_deploy.ARDUINO_SKETCH_FILEPATH,
                [
                    (
                        "#define ON_SIGNAL ---REPLACE_ME---",
                        f"#define ON_SIGNAL {build_arduino_sketch_and_deploy.ON_SIGNAL}",
                    ),
                    (
                        "#define OFF_SIGNAL ---REPLACE_ME---",
                        f"#define OFF_SIGNAL {build_arduino_sketch_and_deploy.OFF_SIGNAL}",
                    ),
                ],
                destination_file.name,
            )
            with open(destination_file.name, "r") as output:
                assert (
                    """#include <RCSwitch.h>

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

#define ON_SIGNAL 123123
#define OFF_SIGNAL 321321

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
    String data = Serial.readStringUntil('\\n');

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
"""
                    == output.read()
                )

    @patch("builtins.open", MockOpenForConfigOnly(read_data=mock_config_file).open)
    @patch("os.system")
    def test_that_it_works(self, mock_os_system):
        reload(build_arduino_sketch_and_deploy)
        with patch.object(
            build_arduino_sketch_and_deploy, "replace_in_file"
        ) as mocked_replace_in_file:
            assert build_arduino_sketch_and_deploy.build_and_deploy()
            mock_os_system.assert_any_call("sudo systemctl stop door-sensor")
            assert mock_os_system.mock_calls[1].startsWith(
                "call('arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi"
            )
            mock_os_system.assert_any_call("sudo systemctl start door-sensor")

            assert mock_os_system.call_count == 3

            mocked_replace_in_file.assert_called_once_with(
                build_arduino_sketch_and_deploy.ARDUINO_SKETCH_FILEPATH,
                [
                    (
                        "#define ON_SIGNAL ---REPLACE_ME---",
                        "#define ON_SIGNAL 123123",
                    ),
                    (
                        "#define OFF_SIGNAL ---REPLACE_ME---",
                        "#define OFF_SIGNAL 321321",
                    ),
                ],
                ANY,  # The destination temp file
            )
