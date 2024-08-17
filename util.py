import datetime
import requests
import json
import base64
from pathlib import Path


def get_timestamp():
    return datetime.datetime.now().isoformat()


def use_hook(hook: str, args: list = [], kwargs: dict = {}) -> dict:
    data = {"hook": hook, "content": {"args": args, "kwargs": kwargs}}
    print(f"Hook call: {hook}, {args}, {kwargs}")
    response = requests.post(f"http://localhost:{HOOK_SERVER_PORT}", json=data)
    print(f"Hook response: {response.json()}")
    return response.json()


def call_tool(route: str, args: list = [], kwargs: dict = {}) -> dict:
    data = {"args": args, "kwargs": kwargs}
    print(f"Tool call: {route}, {args}, {kwargs}")
    response = requests.post(f"http://localhost:{TOOL_SERVER_PORT}/{route}", json=data)
    print(f"Tool response: {response.json()}")
    return response.json()


def file_to_base64(file_path):
    extension = Path(file_path).suffix
    image_base64 = base64.b64encode(open(file_path, "rb").read()).decode("utf-8")
    image_base64_formatted = f"data:image/{extension[1:]};base64," + image_base64
    return image_base64_formatted


HOME_AGENT_DIR = "/home/agent"

CLOCK_JSONL_PATH = HOME_AGENT_DIR + "/clock_events.jsonl"
CLOCK_PY_PATH = HOME_AGENT_DIR + ".agent_code/clock.py"
HOOK_ACTIVITY_LOG_PATH = HOME_AGENT_DIR + "/.agent_code/hooks_activity.jsonl"
HOOK_SERVER_PORT = 8023
HUMAN_AGENT_INFO_PATH = HOME_AGENT_DIR + "/human_agent_info.txt"
INITIAL_SETUP_PATH = HOME_AGENT_DIR + "/.agent_code/initial_setup.py"
INTERNAL_CLOCK_JSONL_PATH = HOME_AGENT_DIR + "/.agent_code/clock_events.jsonl"
INTERNAL_SETTINGS_JSON_PATH = HOME_AGENT_DIR + "/.agent_code/settings.json"
INTERNAL_SUBMISSION_PATH = HOME_AGENT_DIR + "/.agent_code/submission.txt"
NOTE_JSONL_PATH = HOME_AGENT_DIR + "/notes.jsonl"
NOTE_PY_PATH = HOME_AGENT_DIR + "/.agent_code/note.py"
ON_HUMAN_ENTRY_PATH = HOME_AGENT_DIR + "/.agent_code/on_human_entry.py"
SETTINGS_PATH = HOME_AGENT_DIR + "/settings.json"
SUBMIT_PY_PATH = HOME_AGENT_DIR + "/.agent_code/submit.py"
TASK_TXT_PATH = HOME_AGENT_DIR + "/task.txt"
TERMINAL_GIF_PATH = HOME_AGENT_DIR + "/.agent_code/terminal.gif"
TERMINAL_GIF_PATH = HOME_AGENT_DIR + "/.agent_code/terminal.gif"
TERMINAL_LOG_PATH = HOME_AGENT_DIR + "/.agent_code/terminal.cast"
TERMINAL_PY_PATH = HOME_AGENT_DIR + "/.agent_code/terminal.py"
TOOL_ACTIVITY_LOG_PATH = HOME_AGENT_DIR + "/.agent_code/tool_activity.jsonl"
TOOL_SERVER_PORT = 8024
TRIMMED_TERMINAL_LOG_PATH = HOME_AGENT_DIR + "/.agent_code/trimmed_terminal.cast"

settings = json.load(open(SETTINGS_PATH))
