import json
import time
import os
from util import (
    get_timestamp,
    CLOCK_JSONL_PATH,
    INTERNAL_CLOCK_JSONL_PATH,
    use_hook,
    tool_log_styles,
)


def record_clock_event(content):
    entry = {"timestamp": get_timestamp(), "content": f"{content}"}
    with open(CLOCK_JSONL_PATH, "a") as file:
        json.dump(entry, file)
        file.write("\n")
    with open(INTERNAL_CLOCK_JSONL_PATH, "a") as file:
        json.dump(entry, file)
        file.write("\n")


def freeze_in_clock_menu():
    print("Clock stopped. Press '1' to start clock.")
    while True:
        if os.name == "nt":  # Windows
            import msvcrt

            if msvcrt.kbhit():
                key = msvcrt.getch().decode("utf-8").lower()
                if key == "1":
                    break
        else:  # Unix/Linux
            import select
            import sys

            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1).lower()
                if key == "1":
                    break
        time.sleep(0.1)  # Short sleep to prevent high CPU usage


def is_clock_running():
    if not os.path.exists(INTERNAL_CLOCK_JSONL_PATH):
        return False
    with open(INTERNAL_CLOCK_JSONL_PATH, "r") as file:
        lines = file.readlines()
        if lines:
            last_event = json.loads(lines[-1])
            if last_event["content"] == "stopped":
                return False
            elif last_event["content"] == "started":
                return True


def main():
    if not os.path.exists(CLOCK_JSONL_PATH):
        with open(CLOCK_JSONL_PATH, "w") as file:
            file.write("")
    while True:
        clock_running = is_clock_running()
        if clock_running:
            print("\nClock status: RUNNING")
            print("1. Stop clock")
            print("2. Exit")
            choice = input("Enter your choice (1 or 2): ")
            if choice == "1":
                record_clock_event("stopped")
                use_hook(
                    "log_with_attributes",
                    args=[
                        tool_log_styles["clock"],
                        f"⏰ Clock stopped at {get_timestamp()}",
                    ],
                )
                use_hook("pause")
                freeze_in_clock_menu()
                use_hook("unpause")
                record_clock_event("started")
                use_hook(
                    "log_with_attributes",
                    args=[
                        tool_log_styles["clock"],
                        f"⏰ Clock started at {get_timestamp()}",
                    ],
                )
                print("Clock restarted.")
            elif choice == "2":
                print("Exiting clock menu.")
                break
        elif not clock_running:
            print("\nClock status: STOPPED")
            print("1. Start clock")
            print("2. Exit")
            choice = input("Enter your choice (1 or 2): ")
            if choice == "1":
                record_clock_event("started")
                use_hook("unpause")
                use_hook(
                    "log_with_attributes",
                    args=[
                        tool_log_styles["clock"],
                        f"⏰ Clock started at {get_timestamp()}",
                    ],
                )
                print("Clock started.")
            elif choice == "2":
                print("Exiting clock menu.")
                break
            else:
                print("Invalid choice. Please try again.")
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
