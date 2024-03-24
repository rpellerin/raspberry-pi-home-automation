import tempfile
import os
import sys
from .config import get_config

CONFIG = get_config()
ON_SIGNAL = CONFIG.get("arduino", "RF_ON_SIGNAL", fallback=None)
OFF_SIGNAL = CONFIG.get("arduino", "RF_OFF_SIGNAL", fallback=None)
SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
ARDUINO_SKETCH_FILEPATH = f"{SCRIPT_DIRECTORY}/../ArduinoSketch/ArduinoSketch.ino"


def replace_in_file(filename, tuples, destination_file):
    with open(filename, "r") as source, open(destination_file, "w") as destination:
        content = source.read()
        for old_string, new_string in tuples:
            content = content.replace(old_string, new_string)
        destination.write(content)


def build_and_deploy():
    if (ON_SIGNAL == None) or (OFF_SIGNAL == None):
        print("Please set RF_ON_SIGNAL & RF_OFF_SIGNAL in config.txt", file=sys.stderr)
        sys.exit(1)

    # After this `with` block, directory `destination_directory` will be automatically deleted.
    with tempfile.TemporaryDirectory() as destination_directory, open(
        f"{destination_directory}/{os.path.basename(destination_directory)}.ino", "x"
    ) as destination_file:
        replace_in_file(
            ARDUINO_SKETCH_FILEPATH,
            [
                (
                    "#define ON_SIGNAL ---REPLACE_ME---",
                    f"#define ON_SIGNAL {ON_SIGNAL}",
                ),
                (
                    "#define OFF_SIGNAL ---REPLACE_ME---",
                    f"#define OFF_SIGNAL {OFF_SIGNAL}",
                ),
            ],
            destination_file.name,
        )
        print(f"Compiling {destination_file.name}...")

        os.system("sudo systemctl stop door-sensor")
        os.system(
            f'arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi "{destination_directory}" && arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:renesas_uno:unor4wifi "{destination_directory}"'
        )
        os.system("sudo systemctl start door-sensor")

    return True
