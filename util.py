import datetime
import requests
import json
import base64
from pathlib import Path


def get_timestamp():
    return datetime.datetime.now().isoformat()


def log_hook(hook: str, args: list = [], kwargs: dict = {}):
    timestamp = get_timestamp()
    content = {"hook": hook, "args": args, "kwargs": kwargs}
    print(f'{{"timestamp": "{timestamp}", "content":{content}}}')
    with open(USE_HOOK_LOG_PATH, "a") as f:
        f.write(f'{{"timestamp": "{timestamp}", "content":{content}}}\n')


def log_hook_output(hook: str, output: dict):
    timestamp = get_timestamp()
    content = {"hook": hook, "output": output}
    print(f'{{"timestamp": "{timestamp}", "content":{content}}}')
    with open(USE_HOOK_LOG_PATH, "a") as f:
        f.write(f'{{"timestamp": "{timestamp}", "content":{content}}}\n')


def use_hook(hook: str, args: list = [], kwargs: dict = {}) -> dict:
    data = {"hook": hook, "content": {"args": args, "kwargs": kwargs}}
    log_hook(hook, args, kwargs)
    print(f"Hook call: {hook}, {args}, {kwargs}")
    response = requests.post(f"http://localhost:{HOOK_SERVER_PORT}", json=data)
    print(f"Hook response: {response.json()}")
    log_hook_output(hook, response.json())
    return response.json()["output"]


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


local_mode = True
HOME_AGENT_DIR = "/home/agent" if not local_mode else "."
AGENT_CODE_DIR = HOME_AGENT_DIR + "/.agent_code" if not local_mode else "."

CLOCK_JSONL_PATH = HOME_AGENT_DIR + "/clock_events.jsonl"
CLOCK_PY_PATH = AGENT_CODE_DIR + "/clock.py"
HOOK_ACTIVITY_LOG_PATH = AGENT_CODE_DIR + "/hooks_activity.jsonl"
USE_HOOK_LOG_PATH = AGENT_CODE_DIR + "/use_hook_activity.jsonl"
HOOK_SERVER_PORT = 8023
HUMAN_AGENT_INFO_PATH = HOME_AGENT_DIR + "/human_agent_info.txt"
INITIAL_SETUP_PATH = AGENT_CODE_DIR + "/initial_setup.py"
INTERNAL_CLOCK_JSONL_PATH = AGENT_CODE_DIR + "/clock_events.jsonl"
INTERNAL_SETTINGS_JSON_PATH = AGENT_CODE_DIR + "/internal_settings.json"
INTERNAL_SUBMISSION_PATH = AGENT_CODE_DIR + "/submission.txt"
NOTE_JSONL_PATH = HOME_AGENT_DIR + "/notes.jsonl"
NOTE_PY_PATH = AGENT_CODE_DIR + "/note.py"
ON_HUMAN_ENTRY_PATH = AGENT_CODE_DIR + "/on_human_entry.py"
SETTINGS_PATH = HOME_AGENT_DIR + "/settings.json"
SUBMIT_PY_PATH = AGENT_CODE_DIR + "/submit.py"
TASK_TXT_PATH = HOME_AGENT_DIR + "/task.txt"
TERMINAL_GIF_PATH = AGENT_CODE_DIR + "/terminal.gif"
TERMINAL_GIF_PATH = AGENT_CODE_DIR + "/terminal.gif"
TERMINAL_LOG_PATH = AGENT_CODE_DIR + "/terminal.cast"
TERMINAL_PY_PATH = AGENT_CODE_DIR + "/terminal.py"
TOOL_ACTIVITY_LOG_PATH = AGENT_CODE_DIR + "/tool_activity.jsonl"
TOOL_SERVER_PORT = 8024
TOOL_SERVER_PATH = AGENT_CODE_DIR + "/tool_server.py"
TRIMMED_TERMINAL_LOG_PATH = AGENT_CODE_DIR + "/trimmed_terminal.cast"

settings = json.load(open(SETTINGS_PATH))
Path(USE_HOOK_LOG_PATH).touch()
Path(HUMAN_AGENT_INFO_PATH).touch()
