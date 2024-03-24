import sys
from .report_weather import send_report


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) >= 2 else None

    if action == None:
        print("No action given.")
        quit()

    if action == "report_weather":
        send_report()
    else:
        print(f"Unknown action: {action}")
