import datetime
import os
import sys
import requests
import json
import base64
from pathlib import Path


def get_timestamp():
    return datetime.datetime.now().isoformat()


def log_hook(hook: str, args: list = [], kwargs: dict = {}):
    timestamp = get_timestamp()
    content = {"hook": hook, "args": args, "kwargs": kwargs}
    with open(USE_HOOK_LOG_PATH, "a") as f:
        f.write(f'{{"timestamp": "{timestamp}", "content":{content}}}\n')


def log_hook_output(hook: str, output: dict):
    timestamp = get_timestamp()
    content = {"hook": hook, "output": output}
    with open(USE_HOOK_LOG_PATH, "a") as f:
        f.write(f'{{"timestamp": "{timestamp}", "content":{content}}}\n')


def use_hook(hook: str, args: list = [], kwargs: dict = {}) -> dict:
    data = {"hook": hook, "content": {"args": args, "kwargs": kwargs}}
    log_hook(hook, args, kwargs)
    response = requests.post(f"http://localhost:{HOOK_SERVER_PORT}/", json=data)
    log_hook_output(hook, response.json())
    return response.json()["output"]


def call_tool(route: str, args: list = [], kwargs: dict = {}) -> dict:
    data = {"args": args, "kwargs": kwargs}
    response = requests.post(f"http://localhost:{TOOL_SERVER_PORT}/{route}", json=data)
    return response.json()


def file_to_base64(file_path):
    extension = Path(file_path).suffix
    image_base64 = base64.b64encode(open(file_path, "rb").read()).decode("utf-8")
    image_base64_formatted = f"data:image/{extension[1:]};base64," + image_base64
    return image_base64_formatted


def get_shell_config_path():
    # Dictionary mapping shell names to their config files
    config_files = {
        "zsh": ".zshrc",
        "bash": ".bashrc",
        "fish": ".config/fish/config.fish",
    }

    # Get the user's home directory
    home_dir = os.path.expanduser("~")

    # Method 1: Check SHELL environment variable
    shell_path = os.environ.get("SHELL", "")

    # Method 2: Check parent process name (works in most Unix-like systems)
    if not shell_path and hasattr(os, "getppid"):
        try:
            with open(f"/proc/{os.getppid()}/comm", "r") as f:
                shell_path = f.read().strip()
        except FileNotFoundError:
            pass  # /proc not available, skip this method

    # Method 3: Check sys.executable for Python shells like IPython
    if not shell_path and "python" in sys.executable:
        shell_path = "python"

    # Extract shell name from the path
    shell_name = os.path.basename(shell_path).lower()

    # Remove version numbers if present (e.g., zsh-5.8)
    shell_name = shell_name.split("-")[0]

    # Special case for Python shells
    if shell_name == "python":
        return "Running in a Python environment. No specific shell config file."

    if shell_name in config_files:
        return str(os.path.join(home_dir, config_files[shell_name]))
    else:
        return f"Configuration file for {shell_name} not found or shell could not be determined."


tool_log_styles = {
    "clock": {"style": {"background-color": "#f7b7c5", "border-color": "#d17b80"}},
    "terminal": {
        "style": {
            "color": "white",
            "background-color": "#424345",
        }
    },
    "note": {
        "style": {
            "color": "#2b2928",
            "padding": "5px",
            "border-radius": "5px",
            "border-width": "thick",
            "background-color": "#f7e2c8",
            "border-color": "#d9b38e",
            "font-style": "italic",
        }
    },
}

local_mode = True if Path("./local.flag").exists() else False
HOME_AGENT_DIR = "/home/agent" if not local_mode else "."
AGENT_CODE_DIR = HOME_AGENT_DIR + "/.agent_code" if not local_mode else "."

CLOCK_JSONL_PATH = HOME_AGENT_DIR + "/clock_events.jsonl"
CLOCK_PY_PATH = AGENT_CODE_DIR + "/clock.py"
HOOK_ACTIVITY_LOG_PATH = AGENT_CODE_DIR + "/hooks_activity.jsonl"
USE_HOOK_LOG_PATH = AGENT_CODE_DIR + "/use_hook_activity.jsonl"
HOOK_SERVER_PORT = 8023
HUMAN_AGENT_INFO_PATH = HOME_AGENT_DIR + "/human_agent_info.txt"
INITIAL_SETUP_PATH = AGENT_CODE_DIR + "/initial_setup.py"
SETUP_FLAG_PATH = AGENT_CODE_DIR + "/setup.flag"
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
TERMINAL_LOG_PATH = AGENT_CODE_DIR + "/terminal.cast"
TERMINAL_PY_PATH = AGENT_CODE_DIR + "/terminal.py"
TOOL_ACTIVITY_LOG_PATH = AGENT_CODE_DIR + "/tool_activity.jsonl"
TOOL_SERVER_PORT = 8024
TOOL_SERVER_PATH = AGENT_CODE_DIR + "/tool_server.py"
TRIMMED_TERMINAL_LOG_PATH = AGENT_CODE_DIR + "/trimmed_terminal.cast"

settings = json.load(open(SETTINGS_PATH))
Path(USE_HOOK_LOG_PATH).touch()
Path(HUMAN_AGENT_INFO_PATH).touch()
