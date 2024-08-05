import csv
import datetime
import time
import os

def record_break(action):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    csv_file = "breaks.csv"
    file_exists = os.path.isfile(csv_file)
    
    with open(csv_file, 'a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Timestamp", "Action"])
        writer.writerow([timestamp, f"Break {action} recorded"])

def start_break():
    record_break("start")
    print("Break started. Press 'y' to end the break.")
    
    start_time = time.time()
    while True:
        if time.time() - start_time >= 60:  # Check if a minute has passed
            print("Break in progress. Press 'y' to end break.")
            start_time = time.time()  # Reset the timer
        
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

    record_break("end")
    print("Break ended.")

def main():
    while True:
        print("\nBreak Tracker Menu:")
        print("1. Start a break")
        print("2. Exit")
        
        choice = input("Enter your choice (1 or 2): ")
        
        if choice == '1':
            start_break()
        elif choice == '2':
            print("Exiting Break Tracker. Good luck!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()