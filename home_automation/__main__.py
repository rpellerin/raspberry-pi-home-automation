import sys
from .report_weather import send_report
from .remote_control import run as remote_control


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) >= 2 else None

    if action == None:
        print("No action given.")
        sys.exit(1)

    if action == "report_weather":
        send_report()
    elif action == "remote_control":
        success = remote_control()
        if not success:
            sys.exit(1)
    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)
