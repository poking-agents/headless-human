import json
import time
import os
from pathlib import Path
from util import (
    get_timestamp,
    TERMINAL_LOG_PATH,
    TRIMMED_TERMINAL_LOG_PATH,
    TERMINAL_JSONL_PATH,
    TERMINAL_GIF_PATH,
    INTERNAL_SUBMISSION_PATH,
    settings,
)
from typing import Dict, List, Tuple
import subprocess


def get_time_from_last_entry_of_cast(cast_file: str | Path) -> float:
    with open(cast_file, "r") as f:
        lines = f.readlines()
        last_line = next(line for line in reversed(lines) if line.strip())
        last_entry = json.loads(last_line)
        return last_entry[0]


def load_cast_file(
    cast_file: str | Path, start_position: int = 0
) -> Tuple[Dict, List, int]:
    events = []
    current_position = start_position
    with open(cast_file, "r") as f:
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


def has_events_with_string(events: List, string: str, number: int) -> bool:
    events_with_string = []
    for event in events:
        if string in event[2]:
            events_with_string.append(event)
    return True if len(events_with_string) >= number else False


def adjust_event_times(events: List, time_offset: float) -> List:
    time_offset_events = []
    for event in events:
        time_offset_events.append(
            [round(event[0] - time_offset, 6), event[1], event[2]]
        )
    return time_offset_events


class LogMonitor:
    def __init__(self, terminal_gifs: bool, fps_cap: int = 4, speed: float = 1):
        self.last_position = 0
        self.last_update = 0
        self.last_cast_time = 0
        self.last_hooks_log_time = 0
        self.fps_cap = fps_cap
        self.terminal_gifs = terminal_gifs
        self.speed = speed
        self.cast_header = None

    def check_for_updates(self):
        try:
            if os.path.getmtime(TERMINAL_LOG_PATH) + 1 > self.last_update:
                self.update_jsonl()
                self.last_update = time.time()
        except Exception as e:
            print(f"Error checking for updates: {e}")

    def update_jsonl(self):
        try:
            cast_header, new_events, current_position = load_cast_file(
                TERMINAL_LOG_PATH, self.last_position
            )
            if cast_header:
                self.cast_header = cast_header
            if new_events:

                # If new events, check if there has been at least 2 minutes since the previous cast OR if there are 3 events with the terminal prefix (i.e 2 complete commands) OR if the internal submission path exists
                hostname = subprocess.run(
                    ["hostname", "-s"], capture_output=True, text=True
                ).stdout.strip()
                raw_terminal_prefix = (
                    r"\r\n\x1b[?2004l\r\x1b[?2004h\x1b]0;"
                    + os.environ["USER"]
                    + "@"
                    + hostname
                    + ":"
                )
                print(repr(raw_terminal_prefix))

                if (
                    # time.time() - self.last_hooks_log_time > 120 or
                    has_events_with_string(new_events, raw_terminal_prefix, 3)
                    or Path(INTERNAL_SUBMISSION_PATH).exists()
                ):

                    new_cast_time = get_time_from_last_entry_of_cast(TERMINAL_LOG_PATH)
                    time_offset_events = adjust_event_times(
                        new_events, self.last_cast_time
                    )
                    self.last_cast_time = new_cast_time
                    self.last_position = current_position

                    # Write to the trimmed terminal cast file, writing the header and then the time offset events
                    self.last_hooks_log_time = time.time()
                    with open(TRIMMED_TERMINAL_LOG_PATH, "w") as f:
                        if self.cast_header:
                            json.dump(self.cast_header, f)
                            f.write("\n")
                        for event in time_offset_events:
                            json.dump(event, f)
                            f.write("\n")

                    entry = {"timestamp": get_timestamp(), "content": new_events}
                    with open(TERMINAL_JSONL_PATH, "a", encoding="utf-8") as jsonl:
                        json.dump(entry, jsonl, ensure_ascii=False)
                        jsonl.write("\n")

                    if self.terminal_gifs:
                        time.sleep(0.1)
                        subprocess.Popen(
                            [
                                "agg",
                                TRIMMED_TERMINAL_LOG_PATH,
                                TERMINAL_GIF_PATH,
                                "--fps-cap",
                                str(self.fps_cap),
                                "--speed",
                                str(self.speed),
                                "--idle-time-limit",
                                "1",
                                "--last-frame-duration",
                                "7",
                            ],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )

        except Exception as e:
            print(f"Error updating JSONL: {e}")


def monitor_log(terminal_gifs: bool, fps_cap: int = 4, speed: float = 1):
    monitor = LogMonitor(terminal_gifs, fps_cap=fps_cap, speed=speed)

    print(
        f"Starting to monitor {TERMINAL_LOG_PATH}. Updates will be written to {TERMINAL_JSONL_PATH}"
    )
    try:
        while True:
            monitor.check_for_updates()
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Monitoring stopped.")


if __name__ == "__main__":

    if not Path(TRIMMED_TERMINAL_LOG_PATH).exists():
        Path(TRIMMED_TERMINAL_LOG_PATH).touch()

    terminal_gifs = True if settings["terminal_gifs"] == "TERMINAL_GIFS" else False
    monitor_log(terminal_gifs, fps_cap=10, speed=4)
