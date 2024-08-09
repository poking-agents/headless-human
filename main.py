import asyncio
import subprocess
import base64
import json
from pathlib import Path
from util import hooks, read_jsonl
from clock import record_clock_event, get_last_clock_event
from datetime import datetime

def file_to_base64(file_path):
    extension = Path(file_path).suffix
    image_base64 = base64.b64encode(open(file_path, "rb").read()).decode("utf-8")
    image_base64_formatted = f"data:image/{extension[1:]};base64," + image_base64
    return image_base64_formatted

async def hooks_log_on_new_jsonl_entry(filepath: Path):
    attributes = await get_style(filepath)
    old_items = list(read_jsonl(filepath))
    while True:
        await asyncio.sleep(1)
        try:
            new_items = list(read_jsonl(filepath))
            if len(new_items) > len(old_items):
                new_item = new_items[-1]
                content = await format_content(new_item, filepath)
                print(f"New item in {filepath}: {new_item}")
                hooks.log_with_attributes(attributes, content)
                old_items = new_items
        except FileNotFoundError:
            hooks.log(f"File not found: {filepath}")
            await asyncio.sleep(5)  # Wait a bit longer before retrying if file is not found

async def format_content(content: str, filepath: Path):
    if filepath.stem == "note":
        return f"📝 Note: {content['content']}"
    elif filepath.stem == "terminal":
        return f"💻 Terminal: {content}"
    elif filepath.stem == "clock":
        clock_data = content
        print(clock_data)
        action = clock_data["content"].split(" ")[-1]
        utc_str = clock_data["timestamp"]
        utc_time = datetime.fromisoformat(utc_str)
        timestamp = utc_time.strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"⏰ Clock {action} at {timestamp}"
    else:
        return content
    
async def hooks_log_on_any_jsonl_change(filepath: Path):
    attributes = await get_style(filepath)
    old_content = None
    while True:
        await asyncio.sleep(1)
        try:
            new_content = read_jsonl(filepath)
            if new_content != old_content:
                old_content = new_content
                content = await format_content(new_content, filepath)
                print(f"Change in {filepath}: {content}")
                hooks.log_with_attributes(attributes, content)
        except FileNotFoundError:
            hooks.log(f"File not found: {filepath}")
            await asyncio.sleep(5)
        

async def get_style(filepath: Path):
    print(filepath)
    if filepath.stem == "note":
        return {'style':{
            'color': '#2b2928',
            'padding': '5px',
            'border-radius': '5px',
            'border-width': 'thick',
            'background-color': '#f7e2c8',
            'border-color': '#d9b38e',
            'font-style': 'italic',
        }
        }
    elif filepath.stem == "terminal":
        return {'style':{
            'color': 'white',
            'background-color': '#424345',
        }
        }
    elif filepath.stem == "clock":
        return {'style':{
            'background-color': '#f7b7c5',
            'border-color':'#d17b80',
        }}
    else:
        return {}

async def monitors(paths: list[Path]):
    tasks = [hooks_log_on_new_jsonl_entry(path) for path in paths]
    tasks += [log_image_on_change("/home/agent/.agent_code/terminal.gif")]
    tasks += [hooks_log_on_any_jsonl_change("/home/agent/.agent_code/terminal.jsonl")]
    tasks += [monitor_submit()]
    await asyncio.gather(*tasks)


async def log_image_on_change(imagepath:Path): 
    # Detect changes in the image file
    base64_image = None
    while True:
        await asyncio.sleep(1)
        try:
            new_base64_image = file_to_base64(imagepath)
            if new_base64_image != base64_image:
                base64_image = new_base64_image
                hooks.log_image(base64_image)
        except FileNotFoundError:
            print(f"File not found: {imagepath}")
            await asyncio.sleep(5)  # Wait a bit longer before retrying if file is not found
            
async def monitor_submit(submission_path = "/home/agent/submission.txt", internal_submission_path = "/home/agent/.agent_code/submission.txt"):
    
    while True:
        await asyncio.sleep(1)
        # check if the submission flag file exists
        if Path("/home/agent/.agent_code/submission.txt").exists():
            # read the submission file
            with open(internal_submission_path, 'r') as file:
                internal_submission = file.read()
            # Copy the submission to the /home/agent/submission.txt file
            with open(submission_path, 'w') as file:
                file.write(internal_submission)
                
            # stop the timer if it is running
            if get_last_clock_event("/home/agent/.agent_code/clock.jsonl") == "Clock started":
                record_clock_event("stopped", "clock.jsonl")
            await asyncio.sleep(1)
            await hooks.submit(internal_submission)
    

async def main(*args):
    task = await hooks.getTask()
    with open("/home/agent/.agent_code/task.txt", "w") as file:
        file.write(f'Internet permissions for this task (where [] means no internet allowed). Permissions: {str(task.permissions)}\n\n')
    with open("/home/agent/.agent_code/task.txt", "a") as file:
        file.write(f'Task instructions: {task.instructions}')
    with open("/home/agent/.agent_code/task.txt", "r") as file:
        task_txt_content = file.read()
    hooks.log_with_attributes({'style':{'background-color':'#bcd4ba'}},f"/home/agent/task.txt:\n{task_txt_content}")
    
    subprocess.check_call(["cp", "/home/agent/settings.json", "/home/agent/.agent_code/settings.json"])
    settings = json.load(open("/home/agent/.agent_code/settings.json"))
    if settings["terminal_gifs"] == "TERMINAL_GIFS":
        subprocess.check_call(["touch", "/home/agent/.agent_code/terminal_gifs.flag"])
        
    # hooks.pause()
    
    # Wait on setup flag before starting monitoring
    setup_flag = Path("/home/agent/.agent_code/setup.flag")
    while not setup_flag.exists():
        await asyncio.sleep(1)
        
    hooks.log_with_attributes({'style':{'background-color':'#bcd3d6'}}, "Setup flag detected. Starting monitoring.")
    
    with open ("/home/agent/human_agent_info.txt", "r") as file:
        file_content = file.read()
    hooks.log(f"/home/agent/human_agent_info.txt:\n{file_content}")
        
    tools = ["note.py", "clock.py"]
    jsonl_files_to_monitor = [tool.replace(".py", ".jsonl") for tool in tools]
    jsonl_paths_to_monitor = [Path(__file__).parent / file for file in jsonl_files_to_monitor]
    jsonl_paths_to_monitor += [Path(__file__).parent / "terminal.jsonl"]
    
    for file in jsonl_paths_to_monitor: 
        file.touch()
    
    monitor_task = asyncio.create_task(monitors(jsonl_paths_to_monitor))
    
    try:
        while True:
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        monitor_task.cancel()
        await monitor_task

        
if __name__ == "__main__":
    hooks.main(main)