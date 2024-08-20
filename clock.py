import json
import time
import os
from util import get_timestamp, CLOCK_JSONL_PATH


def record_clock_event(content):
    entry = {"timestamp": get_timestamp(), "content": content}

    with open(CLOCK_JSONL_PATH, "a") as file:
        json.dump(entry, file)
        file.write("\n")


def wait_for_key(target_key="y"):
    print(f"Press '{target_key}' to continue...")
    while True:
        if os.name == "nt":  # Windows
            import msvcrt

            if msvcrt.kbhit():
                key = msvcrt.getch().decode("utf-8").lower()
                if key == target_key:
                    return
        else:  # Unix/Linux
            import select
            import sys

            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1).lower()
                if key == target_key:
                    return

        time.sleep(0.1)  # Short sleep to prevent high CPU usage


def stop_clock():
    record_clock_event("stopped")
    print("Clock stopped. Press 'y' to resume.")
    wait_for_key("y")
    record_clock_event("started")
    print("Clock resumed.")


def get_last_clock_event():
    if not os.path.exists(CLOCK_JSONL_PATH):
        return None

    with open(CLOCK_JSONL_PATH, "r") as file:
        lines = file.readlines()
        if lines:
            last_event = json.loads(lines[-1])
            return last_event["content"]
    return None


def main():
    while True:
        last_event = get_last_clock_event()
        clock_running = last_event != "stopped" if last_event else False

        print("")
        print(f"Current status: {'Running' if clock_running else 'Stopped'}")
        if clock_running:
            print("p: Pause clock")
            print("e: Exit")
            choice = input("Enter your choice (p or e): ")
            if choice == "p":
                stop_clock()
            elif choice == "e":
                print("Exiting clock menu.")
                break
            else:
                print("Invalid choice. Please try again.")

        elif not clock_running:
            print("s: Start clock")
            print("e: Exit")
            choice = input("Enter your choice (s or e): ")
            if choice == "s":
                record_clock_event("started")
                print("Clock started.")
            elif choice == "e":
                print("Exiting clock menu.")
                break
            else:
                print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
