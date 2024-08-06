import json
import datetime
import time
import os
from util import set_human_env_vars

def record_clock_event(action):
    timestamp = datetime.datetime.now().isoformat()
    jsonl_file = "clock_events.jsonl"
    
    entry = {
        "timestamp": timestamp,
        "action": f"Clock {action}"
    }
    
    with open(jsonl_file, 'a') as file:
        json.dump(entry, file)
        file.write('\n')

def stop_clock():
    record_clock_event("stopped")
    print("Clock stopped. Press 'y' to end break.")
    
    while True:
        if os.name == 'nt':  # Windows
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
                if key == 'y':
                    break
        else:  # Unix/Linux
            import select
            import sys
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1).lower()
                if key == 'y':
                    break
        
        time.sleep(0.1)  # Short sleep to prevent high CPU usage
    
    record_clock_event("started")
    print("Clock started.")

def get_last_clock_event():
    jsonl_file = "clock_events.jsonl"
    if not os.path.exists(jsonl_file):
        return None
    
    with open(jsonl_file, 'r') as file:
        lines = file.readlines()
        if lines:
            last_event = json.loads(lines[-1])
            return last_event['action']
    return None

def main():
    set_human_env_vars()
    
    while True:
        last_event = get_last_clock_event()
        clock_running = last_event != "Clock stopped" if last_event else False

        print("\nClock Menu:")
        print("1. Start clock")
        print("2. Stop clock")
        print("3. Exit")
        
        choice = input("Enter your choice (1, 2, or 3): ")
        
        if choice == '1':
            if clock_running:
                print("Clock is already running.")
            else:
                record_clock_event("started")
                print("Clock started.")
        elif choice == '2':
            if clock_running:
                stop_clock()
            else:
                print("Clock is not running. Start the clock first.")
        elif choice == '3':
            print("Exiting clock menu.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()