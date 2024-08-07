import os
import asyncio
import json
from pyhooks import Hooks, Actions
hooks = Hooks()
actions = Actions()

AGENT_CODE_DIR = ".agent_code"

def read_jsonl(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            yield json.loads(line.strip())

async def hooks_log_on_file_change(filepath):
    # Listen for changes to the file
    with open(filepath, "r") as f:
        old_contents = f.read()
        
    while True:
        await asyncio.sleep(1)
        try:
            with open(filepath, "r") as f:
                new_contents = f.read()
            if new_contents != old_contents:
                hooks.log(f"File changed: {filepath}")
                hooks.log(f"New content: {new_contents}")
                old_contents = new_contents
        except FileNotFoundError:
            hooks.log(f"File not found: {filepath}")
            await asyncio.sleep(5)  # Wait a bit longer before retrying if file is not found

# Unused below

def set_human_env_vars():
    # Set the agent token since this not available when humans ssh in with `mp4 code`
    with open("agent_token.txt", "r") as f:
        agent_token = f.read()
        os.environ["AGENT_TOKEN"] = agent_token
    with open("run_id.txt", "r") as f:
        run_id = f.read()
        os.environ["RUN_ID"] = run_id
    os.environ["API_URL"] = "https://mp4-server.koi-moth.ts.net/api"
    

async def write_agent_token():
    with open(".agent_code/agent_token.txt", "w") as f:
        f.write(os.getenv("AGENT_TOKEN"))
    with open(".agent_code/run_id.txt", "w") as f:
        f.write(os.getenv("RUN_ID"))
    return None