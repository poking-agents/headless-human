import os
import asyncio
import json
from util import hooks, read_jsonl
from pyhooks.types import MiddlemanSettings, RunUsageAndLimits

async def write_agent_token():
    with open(".agent_code/agent_token.txt", "w") as f:
        f.write(os.getenv("AGENT_TOKEN"))
    with open(".agent_code/run_id.txt", "w") as f:
        f.write(os.getenv("RUN_ID"))
    return None


async def hooks_log_on_new_jsonl_entry(filepath):
    # Listen for new entries in the jsonl file
    
    all_items = list(read_jsonl(filepath))
    while True:
        await asyncio.sleep(1)
        try:
            with open(filepath, "r") as f:
                new_items = list(read_jsonl(filepath))
            if len(new_items) > len(all_items):
                new_item = new_items[-1]
                hooks.log(f"New entry in {filepath}:\n{new_item}")
                all_items = new_items
        except FileNotFoundError:
            hooks.log(f"File not found: {filepath}")
            await asyncio.sleep(5)  # Wait a bit longer before retrying if file is not found
    

async def monitor_jsonl_files(files):
    tasks = [hooks_log_on_new_jsonl_entry(file) for file in files]
    await asyncio.gather(*tasks)

async def main(*args):
        
    usage = await hooks.get_usage()
    hooks.log(f"Usage: {usage}")
    task = await hooks.getTask()
    hooks.log(f"Task: {task}")
    
    jsonl_files_to_monitor = [".agent_code/notes.jsonl", ".agent_code/clock_events.jsonl", ".agent_code/terminal.jsonl"]
    
    for file in jsonl_files_to_monitor:
        if not os.path.exists(file):
            with open(file, "w") as f:
                f.write("")

    
    await write_agent_token() # So that agent token is available when humans use `mp4 code`
    
    # Now monitor and hooks.log changes to .agent_code/notes.jsonl and breaks.jsonl
    monitor_task = asyncio.create_task(monitor_jsonl_files(jsonl_files_to_monitor))
    
    
    
    try:
        while True:
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        monitor_task.cancel()
        await monitor_task
        
if __name__ == "__main__":
    hooks.main(main)