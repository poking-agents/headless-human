import json
import time
import os
from pathlib import Path
from util import AGENT_CODE_DIR, get_timestamp


def record_clock_event(content, jsonl_path):
    
    entry = {
        "timestamp": get_timestamp(),
        "content": f"Clock {content}"
    }
    
    with open(jsonl_path, 'a') as file:
        json.dump(entry, file)
        file.write('\n')

def stop_clock(jsonl_path):
    record_clock_event("stopped", jsonl_path)
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
    
    record_clock_event("started", jsonl_path)
    print("Clock started.")

def get_last_clock_event(jsonl_path):
    if not os.path.exists(jsonl_path):
        return None
    
    with open(jsonl_path, 'r') as file:
        lines = file.readlines()
        if lines:
            last_event = json.loads(lines[-1])
            return last_event['content']
    return None

def main():
    jsonl_path = Path(__file__).parent / f"{Path(__file__).stem}.jsonl"
    while True:
        last_event = get_last_clock_event(jsonl_path = jsonl_path)
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
                record_clock_event("started", jsonl_path)
                print("Clock started.")
        elif choice == '2':
            if clock_running:
                stop_clock(jsonl_path)
            else:
                print("Clock is not running. Start the clock first.")
        elif choice == '3':
            print("Exiting clock menu.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()