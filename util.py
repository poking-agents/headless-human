import json
from pyhooks import Hooks, Actions
import datetime
hooks = Hooks()
actions = Actions()

AGENT_CODE_DIR = ".agent_code"

def read_jsonl(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            yield json.loads(line.strip())

def get_timestamp():
    return datetime.datetime.now().isoformat()