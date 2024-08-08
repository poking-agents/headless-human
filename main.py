import asyncio
from pathlib import Path
from util import hooks, read_jsonl
from pyhooks.types import MiddlemanSettings, RunUsageAndLimits
from datetime import datetime
import base64

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
        return {}  # Default style if no match

async def monitor_jsonl_files(paths: list[Path]):
    tasks = [hooks_log_on_new_jsonl_entry(path) for path in paths]
    tasks += [log_image_on_change("/home/agent/.agent_code/terminal.gif")]
    tasks += [hooks_log_on_any_jsonl_change("/home/agent/.agent_code/terminal.jsonl")]
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


async def main(*args):

    task = await hooks.getTask()
    hooks.log_with_attributes({'style':{'background-color':'#bcd4ba'}},f"Task: {task}")

    
    tools = ["note.py", "clock.py"]
    jsonl_files_to_monitor = [tool.replace(".py", ".jsonl") for tool in tools]
    jsonl_paths_to_monitor = [Path(__file__).parent / file for file in jsonl_files_to_monitor]
    jsonl_paths_to_monitor += [Path(__file__).parent / "terminal.jsonl"]
    
    for file in jsonl_paths_to_monitor: 
        file.touch()  # Create the file if it doesn't exist
    
    monitor_task = asyncio.create_task(monitor_jsonl_files(jsonl_paths_to_monitor))
    
    try:
        while True:
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        monitor_task.cancel()
        await monitor_task

        
if __name__ == "__main__":
    hooks.main(main)
