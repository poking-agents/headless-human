import json
import time
import os
from datetime import datetime
from util import hooks



class LogMonitor:
    def __init__(self, log_file, buffer_file, jsonl_file):
        self.log_file = log_file
        self.buffer_file = buffer_file
        self.jsonl_file = jsonl_file
        self.last_position = 0
        self.last_update = 0
        self.last_modified = 0
        
        os.system("asciinema rec /home/agent/.agent_code/terminal.cast --overwrite -q")

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

                    # If new content string doesn't contain a '\r' caharacter, skip this update, and store the unused content
                    if '\r' not in new_content_str:
                        with open(self.buffer_file, 'a', encoding = 'utf-8') as buffer:
                            buffer.write(new_content_str)
                    else:
                        # run in foreground
                        # Exit the asciinema recording
                        os.system("bash -c 'fg; exit'")
                        # Create a gif from the cast using agg
                        os.system("agg /home/agent/.agent_code/terminal.cast /home/agent/.agent_code/terminal.gif --fps-cap 2 &")
                        # Restart the asciinema recording
                        os.system("bash -c 'fg; asciinema rec /home/agent/.agent_code/terminal.cast --overwrite -q'")
                        
                        # Prepend unused content from buffer file
                        with open(self.buffer_file, 'r', encoding='utf-8') as buffer:
                            unused_content = buffer.read()
                        new_content_str = unused_content + new_content_str
                        # Wipe buffer file
                        with open(self.buffer_file, 'w', encoding = 'utf-8') as buffer:
                            buffer.write('')
                        
                        entry = {
                            "timestamp": timestamp,
                            "content": new_content_str
                        }
                        with open(self.jsonl_file, 'a', encoding='utf-8') as jsonl:
                            json.dump(entry, jsonl, ensure_ascii=False)
                            jsonl.write('\n')
                            
        except Exception as e:
            print(f"Error updating JSONL: {e}")

def monitor_log(log_file, buffer_file, jsonl_file):
    monitor = LogMonitor(log_file, buffer_file, jsonl_file)

    print(f"Starting to monitor {log_file}. Updates will be written to {jsonl_file}")
    try:
        while True:
            monitor.check_for_updates()
            time.sleep(1)  # Check every second
    except KeyboardInterrupt:
        print("Monitoring stopped.")

if __name__ == "__main__":
    log_file = "/home/agent/.agent_code/mysession.log"
    jsonl_file = "/home/agent/.agent_code/terminal.jsonl"
    buffer_file = log_file + ".buffer"

    if not os.path.exists(log_file):
        with open(log_file, 'w') as f:
            f.write("")
    if not os.path.exists(buffer_file):
        with open(buffer_file, 'w') as f:
            f.write("")
        
        
    monitor_log(log_file,buffer_file, jsonl_file)