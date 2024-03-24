import sys
from .report_weather import send_report
from .remote_control import run as remote_control
from .build_arduino_sketch_and_deploy import build_and_deploy


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) >= 2 else None

    if action == None:
        print("No action given.")
        sys.exit(1)

    success = False
    if action == "report_weather":
        success = send_report()
    elif action == "remote_control":
        success = remote_control()
    elif action == "build_arduino_sketch_and_deploy":
        success = build_and_deploy()
    else:
        print(f"Unknown action: {action}", file=sys.stderr)

    if not success:
        sys.exit(1)
