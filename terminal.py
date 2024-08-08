import json
import time
import os
from util import get_timestamp
from typing import Dict, List, Tuple
import subprocess

def get_time_from_last_entry_of_cast(cast_file):
    with open(cast_file, 'r') as f:
        lines = f.readlines()
        last_line = next(line for line in reversed(lines) if line.strip())
        last_entry = json.loads(last_line)
        return last_entry[0]
    
def load_cast_file(cast_file, start_position = 0) -> Tuple[Dict, List, int]:
    events = []
    current_position = start_position
    with open(cast_file, 'r') as f:
        f.seek(start_position)
        if start_position == 0:
            header = json.loads(f.readline())
            current_position = f.tell()
        else:
            header = None
        
        line_count = 0
        for line in f:
            if line.strip():
                events.append(json.loads(line))
                line_count += 1
        current_position = f.tell()
        return header, events, current_position
            
def has_events_with_string(events: List, string:str) -> bool:
    events_with_string = []
    for event in events:
        if string in event[2]:
            events_with_string.append(event)
    return True if events_with_string else False

def round_to_sig_figs(num: float, sig_figs: int) -> float:
    return float(f"{num:.{sig_figs}g}")

def adjust_event_times(events: List, time_offset: float) -> List:
    time_offset_events = []
    for event in events:
        time_offset_events.append([round(event[0] - time_offset,6) , event[1], event[2]])
    return time_offset_events

class LogMonitor:
    def __init__(self, log_file, jsonl_file, trimmed_cast_file, gif_file, fps_cap=4, speed =1):
        self.log_file = log_file
        self.jsonl_file = jsonl_file
        self.trimmed_cast_file = trimmed_cast_file
        self.gif_file = gif_file
        self.last_position = 0
        self.last_update = 0
        self.last_modified = 0
        self.last_cast_time = 0
        self.fps_cap = fps_cap
        self.speed = speed
        self.cast_header = None

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
            cast_header, new_events, current_position = load_cast_file(self.log_file, self.last_position)
            if cast_header:
                self.cast_header = cast_header
            if new_events:
                
                # If new events, check for '/r' in the content
                if has_events_with_string(new_events, '\r'):
                    
                    new_cast_time = get_time_from_last_entry_of_cast(self.log_file)
                    time_offset_events = adjust_event_times(new_events, self.last_cast_time)
                    self.last_cast_time = new_cast_time
                    self.last_position = current_position
                    
                    # Write to the trimmed terminal cast file, writing the header and then the time offset events
                    with open(self.trimmed_cast_file, 'w') as f:
                        if self.cast_header:
                            json.dump(self.cast_header, f)
                            f.write('\n')
                        for event in time_offset_events:
                            json.dump(event, f)
                            f.write('\n')
                    
                    subprocess.Popen(["agg", self.trimmed_cast_file, self.gif_file, "--fps-cap", str(self.fps_cap), "--speed", str(self.speed)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
                        
                    entry = {
                        "timestamp": get_timestamp(),
                        "content":  new_events 
                    }
                    with open(self.jsonl_file, 'a', encoding='utf-8') as jsonl:
                        json.dump(entry, jsonl, ensure_ascii=False)
                        jsonl.write('\n')
                            
        except Exception as e:
            print(f"Error updating JSONL: {e}")

def monitor_log(log_file, jsonl_file, trimmed_cast_file, gif_file, fps_cap=4, speed=1):
    monitor = LogMonitor(log_file, jsonl_file, trimmed_cast_file, gif_file, fps_cap=fps_cap, speed=speed)

    print(f"Starting to monitor {log_file}. Updates will be written to {jsonl_file}")
    try:
        while True:
            monitor.check_for_updates()
            time.sleep(1)  # Check every second
    except KeyboardInterrupt:
        print("Monitoring stopped.")

if __name__ == "__main__":
    log_file = "/home/agent/.agent_code/terminal.cast"
    jsonl_file = "/home/agent/.agent_code/terminal.jsonl"
    trimmed_cast_file = "/home/agent/.agent_code/trimmed_terminal.cast"
    gif_file = "/home/agent/.agent_code/terminal.gif"
    
    log_file = "terminal.cast"
    jsonl_file = "terminal.jsonl"
    trimmed_cast_file = "trimmed_terminal.cast"
    gif_file = "terminal.gif"
    
    if not os.path.exists(trimmed_cast_file):
        with open(trimmed_cast_file, 'w') as f:
            f.write('')
                
    monitor_log(log_file, jsonl_file, trimmed_cast_file, gif_file, fps_cap=4, speed=1)