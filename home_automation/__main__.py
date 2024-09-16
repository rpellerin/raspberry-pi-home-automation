import sys
from .remote_control import run as remote_control


def run(action):
    if action == None:
        print("No action given.", file=sys.stderr)
        return False

    if action == "report_weather":
        from .report_weather import send_report  # Lazy import

        return send_report()
    elif action == "remote_control":
        from .remote_control import run as remote_control

        return remote_control()
    elif action == "build_arduino_sketch_and_deploy":
        from .build_arduino_sketch_and_deploy import build_and_deploy

        return build_and_deploy()
    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        return False


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) >= 2 else None
    if not run(action):
        sys.exit(1)
