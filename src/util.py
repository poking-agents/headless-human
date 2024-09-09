import datetime
import json
import pathlib

import pyhooks

LOCAL_MODE = (pathlib.Path.cwd() / "local.flag").exists()

AGENT_HOME_DIR = pathlib.Path.cwd() if LOCAL_MODE else pathlib.Path("/home/agent")
AGENT_CODE_DIR = pathlib.Path(__file__).parents[1] if LOCAL_MODE else AGENT_HOME_DIR / ".agent_code"

HOOKS = pyhooks.Hooks()
INSTRUCTIONS_FILE = AGENT_HOME_DIR / "instructions.txt"
INTERNAL_SUBMISSION_PATH = AGENT_CODE_DIR / "submission.txt"
RUN_INFO_FILE = AGENT_CODE_DIR / "run_info.json"


def get_settings():
    return json.loads(RUN_INFO_FILE.read_text())


def get_timestamp():
    return datetime.datetime.now().isoformat()
