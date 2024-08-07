import json
import time
import os
from datetime import datetime

class LogMonitor:
    def __init__(self, log_file, jsonl_file):
        self.log_file = log_file
        self.jsonl_file = jsonl_file
        self.last_position = 0
        self.last_update = 0
        self.last_modified = 0

    def check_for_updates(self):
        try:
            current_modified = os.path.getmtime(self.log_file)
            if current_modified > self.last_modified:
                current_time = time.time()
                if current_time - self.last_update >= 1:  # 1-second buffer
                    self.update_jsonl()
                    self.last_update = current_time
                    self.last_modified = current_modified
        except Exception as e:
            print(f"Error checking for updates: {e}")

    def update_jsonl(self):
        try:
            with open(self.log_file, 'rb') as log:
                log.seek(self.last_position)
                new_content = log.read()
                if new_content:
                    self.last_position = log.tell()
                    timestamp = datetime.now().isoformat()

                    # Try to decode as UTF-8, replace invalid characters
                    try:
                        new_content_str = new_content.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        # If UTF-8 fails, try latin-1 (which should never fail)
                        new_content_str = new_content.decode('latin-1')

                    entry = {
                        "timestamp": timestamp,
                        "content": new_content_str
                    }
                    with open(self.jsonl_file, 'a', encoding='utf-8') as jsonl:
                        json.dump(entry, jsonl, ensure_ascii=False)
                        jsonl.write('\n')
        except Exception as e:
            print(f"Error updating JSONL: {e}")

def monitor_log(log_file, jsonl_file):
    monitor = LogMonitor(log_file, jsonl_file)

    print(f"Starting to monitor {log_file}. Updates will be written to {jsonl_file}")
    try:
        while True:
            monitor.check_for_updates()
            time.sleep(1)  # Check every second
    except KeyboardInterrupt:
        print("Monitoring stopped.")

if __name__ == "__main__":
    log_file = "mysession.log"
    jsonl_file = "terminal.jsonl"

    if not os.path.exists(log_file):
        with open(log_file, 'w') as f:
            f.write("")
    monitor_log(log_file, jsonl_file)