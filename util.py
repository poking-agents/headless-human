import json
import os
import base64
from pathlib import Path
from pyhooks import Hooks, Actions
import datetime

hooks = Hooks()
actions = Actions()

CLOCK_JSONL_PATH = f"/home/agent/.agent_code/clock.jsonl"
CLOCK_PY_PATH = f"/home/agent/.agent_code/clock.py"
HUMAN_AGENT_INFO_PATH = f"/home/agent/human_agent_info.txt"
INTERNAL_SETTINGS_JSON_PATH = f"/home/agent/.agent_code/settings.json"
SUBMISSION_PATH = f"/home/agent/submission.txt"
INTERNAL_SUBMISSION_PATH = f"/home/agent/.agent_code/internal_submission.txt"
INTERNAL_TASK_TXT_PATH = f"/home/agent/.agent_code/task.txt"
NOTE_JSONL_PATH = f"/home/agent/.agent_code/note.jsonl"
NOTE_PY_PATH = f"/home/agent/.agent_code/note.py"
SETUP_FLAG_PATH = f"/home/agent/.agent_code/setup.flag"
TERMINAL_GIF_PATH = f"/home/agent/.agent_code/terminal.gif"
TERMINAL_JSONL_PATH = f"/home/agent/.agent_code/terminal.jsonl"
TERMINAL_PY_PATH = f"/home/agent/.agent_code/terminal.py"
TERMINAL_LOG_PATH = "/home/agent/.agent_code/terminal.cast"
TRIMMED_TERMINAL_LOG_PATH = "/home/agent/.agent_code/trimmed_terminal.cast"
SETUP_SCRIPT_PATH = "/home/agent/.agent_code/setup.sh"

PATHS = {
    "CLOCK_JSONL_PATH": CLOCK_JSONL_PATH,
    "CLOCK_PY_PATH": CLOCK_PY_PATH,
    "HUMAN_AGENT_INFO_PATH": HUMAN_AGENT_INFO_PATH,
    "INTERNAL_SETTINGS_JSON_PATH": INTERNAL_SETTINGS_JSON_PATH,
    "SUBMISSION_PATH": SUBMISSION_PATH,
    "INTERNAL_SUBMISSION_PATH": INTERNAL_SUBMISSION_PATH,
    "INTERNAL_TASK_TXT_PATH": INTERNAL_TASK_TXT_PATH,
    "NOTE_JSONL_PATH": NOTE_JSONL_PATH,
    "NOTE_PY_PATH": NOTE_PY_PATH,
    "SETUP_FLAG_PATH": SETUP_FLAG_PATH,
    "TERMINAL_GIF_PATH": TERMINAL_GIF_PATH,
    "TERMINAL_JSONL_PATH": TERMINAL_JSONL_PATH,
    "TERMINAL_PY_PATH": TERMINAL_PY_PATH,
    "TERMINAL_LOG_PATH": TERMINAL_LOG_PATH,
    "TRIMMED_TERMINAL_LOG_PATH": TRIMMED_TERMINAL_LOG_PATH,
}

settings = json.load(open("/home/agent/settings.json"))


def read_jsonl(file_path):
    with open(file_path, "r") as file:
        for line in file:
            yield json.loads(line.strip())


def get_timestamp():
    return datetime.datetime.now().isoformat()


def is_clock_running():
    if not os.path.exists(CLOCK_JSONL_PATH):
        return False
    with open(CLOCK_JSONL_PATH, "r") as file:
        lines = file.readlines()
        if lines:
            last_event = json.loads(lines[-1])
            if last_event["content"] == "stopped":
                return False
            elif last_event["content"] == "started":
                return True


def file_to_base64(file_path):
    extension = Path(file_path).suffix
    image_base64 = base64.b64encode(open(file_path, "rb").read()).decode("utf-8")
    image_base64_formatted = f"data:image/{extension[1:]};base64," + image_base64
    return image_base64_formatted


if __name__ == "__main__":
    for key, value in PATHS.items():
        print(f'export {key}="{value}"')
