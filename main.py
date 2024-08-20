import asyncio
import subprocess
from strip_ansi import strip_ansi
from pathlib import Path
from util import (
    hooks,
    read_jsonl,
    file_to_base64,
    CLOCK_JSONL_PATH,
    HUMAN_AGENT_INFO_PATH,
    INTERNAL_SETTINGS_JSON_PATH,
    INTERNAL_SUBMISSION_PATH,
    INTERNAL_TASK_TXT_PATH,
    NOTE_JSONL_PATH,
    SETUP_FLAG_PATH,
    SUBMISSION_PATH,
    TASK_TXT_PATH,
    TERMINAL_GIF_PATH,
    TERMINAL_JSONL_PATH,
)
from datetime import datetime


def process_terminal_nested_list(input_list):
    # result = ""
    # for item in input_list:
    #     _, _, char = item
    #     result += char

    # # Split the result into lines and join with double newlines
    # lines = result.split("\r\n")
    # joined = "\n".join(lines)
    # return joined
    result = ""
    print(input_list)
    for l in input_list:
        # print(f'list:{l}')
        _, _, string = l
        print(f"string:{string}")
        # Remove all ansi control codes e.g \x1b...
        string = strip_ansi(string)
        print("")
        print(f"new string:{string}")
        result += string

    # Split the result into lines and join with double newlines
    lines = result.split("\n")
    return "\n".join(lines)


async def hooks_log_on_new_jsonl_entry(filepath: Path):
    attributes = await get_style(filepath)
    old_items = list(read_jsonl(filepath))
    while True:
        await asyncio.sleep(1)
        try:
            new_items = list(read_jsonl(filepath))
            if len(new_items) > len(old_items):
                new_item = new_items[-1]
                content = await format_json(new_item, filepath)
                print(f"New item in {filepath}: {new_item}")
                if filepath.stem == "clock":
                    if new_item["content"] == "started":
                        await hooks.unpause()
                        hooks.log_with_attributes(attributes, content)
                    elif new_item["content"] == "stopped":
                        hooks.log_with_attributes(attributes, content)
                        await asyncio.sleep(1)
                        await hooks.pause()
                else:
                    hooks.log_with_attributes(attributes, content)
                old_items = new_items

        except FileNotFoundError:
            hooks.log(f"File not found: {filepath}")
            await asyncio.sleep(
                5
            )  # Wait a bit longer before retrying if file is not found


async def format_json(json: dict, filepath: Path):
    if filepath.stem == "note":
        return f"📝 Note:\n{json['content']}"
    elif filepath.stem == "terminal":
        content = process_terminal_nested_list(json["content"])
        return f"💻 Terminal:\n{content}"
    elif filepath.stem == "clock":
        utc_str = json["timestamp"]
        utc_time = datetime.fromisoformat(utc_str)
        timestamp = utc_time.strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"⏰ Clock {json['content']} at {timestamp}"
    else:
        return json


@hooks.frame("Raw Terminal Log")
async def terminal_log(attributes: dict, content: str):
    return await hooks.log_with_attributes(attributes, content)


async def hooks_log_on_any_jsonl_change(filepath: Path) -> None:
    attributes = await get_style(filepath)
    old_content = None
    while True:
        await asyncio.sleep(1)
        try:
            new_content = read_jsonl(filepath)
            if new_content != old_content:
                old_content = new_content
                content = await format_json(new_content, filepath)
                print(f"Change in {filepath}: {content}")
                if filepath.stem == "terminal":
                    await terminal_log(attributes, content)
                else:
                    hooks.log_with_attributes(attributes, content)
        except FileNotFoundError:
            hooks.log(f"File not found: {filepath}")
            await asyncio.sleep(5)


async def get_style(filepath: Path) -> dict:
    print(filepath)
    if filepath.stem == "note":
        return {
            "style": {
                "color": "#2b2928",
                "padding": "5px",
                "border-radius": "5px",
                "border-width": "thick",
                "background-color": "#f7e2c8",
                "border-color": "#d9b38e",
                "font-style": "italic",
            }
        }
    elif filepath.stem == "terminal":
        return {
            "style": {
                "color": "white",
                "background-color": "#424345",
            }
        }
    elif filepath.stem == "clock":
        return {
            "style": {
                "background-color": "#f7b7c5",
                "border-color": "#d17b80",
            }
        }
    else:
        return {}


async def monitors(paths: list[Path]) -> None:
    tasks = [hooks_log_on_new_jsonl_entry(path) for path in paths]
    tasks += [log_image_on_change(Path(TERMINAL_GIF_PATH))]
    tasks += [hooks_log_on_any_jsonl_change(Path(TERMINAL_JSONL_PATH))]
    tasks += [monitor_submit()]
    await asyncio.gather(*tasks)


async def log_image_on_change(imagepath: Path) -> None:
    # Detect changes in the image file
    base64_image = None
    while True:
        await asyncio.sleep(1)
        try:
            new_base64_image = file_to_base64(imagepath)
            if new_base64_image != base64_image:
                base64_image = new_base64_image
                await asyncio.sleep(0.35)
                hooks.log_image(base64_image)
        except FileNotFoundError:
            print(f"File not found: {imagepath}")
            await asyncio.sleep(
                5
            )  # Wait a bit longer before retrying if file is not found


async def monitor_submit() -> None:

    while True:
        await asyncio.sleep(1)
        if Path(INTERNAL_SUBMISSION_PATH).exists():
            with open(INTERNAL_SUBMISSION_PATH, "r") as file:
                internal_submission = file.read()
            with open(SUBMISSION_PATH, "w") as file:
                file.write(internal_submission)

            await asyncio.sleep(10)  # For tool processes to submit last logs
            await hooks.submit(internal_submission)


async def get_task_txt_content(task: dict) -> str:
    content = f"""Internet permissions for this task (where [] means no internet allowed). Permissions:{str(task.permissions)}

Task instructions: {task.instructions}"""
    return content


async def main(*args) -> None:

    await hooks.pause()
    task = await hooks.getTask()
    task_txt_content = await get_task_txt_content(task)
    with open(INTERNAL_TASK_TXT_PATH, "w") as file:
        file.write(task_txt_content)
    with open(HUMAN_AGENT_INFO_PATH, "w") as file:
        file.write(task_txt_content)
    hooks.log_with_attributes(
        {"style": {"background-color": "#bcd4ba"}},
        f"{INTERNAL_TASK_TXT_PATH}:\n{task_txt_content}",
    )
    subprocess.check_call(["cp", INTERNAL_TASK_TXT_PATH, TASK_TXT_PATH])

    Path(INTERNAL_SETTINGS_JSON_PATH).touch()
    subprocess.check_call(
        ["cp", "/home/agent/settings.json", INTERNAL_SETTINGS_JSON_PATH]
    )

    # Adds a line that auto runs setup on agent user login shells (i.e when human logs in with --user agent)
    subprocess.run(
        'echo "bash /home/agent/.agent_code/setup.sh" >> /home/agent/.profile',
        shell=True,
        check=True,
    )

    # Install agg
    # ONLY WORKS ON THE DEFAULT MACHINE (precompiled binary)
    # WILL FIX WHEN AGENTS CAN HAVE NON-PYTHON DEPENDENCIES
    subprocess.check_call(["chmod", "+x", ".agent_code/agg"])
    subprocess.check_call(["cp", ".agent_code/agg", "/home/agent/.local/bin/agg"])

    # Wait on setup flag before starting monitoring
    setup_flag = Path(SETUP_FLAG_PATH)
    while not setup_flag.exists():
        await asyncio.sleep(1)

    with open(HUMAN_AGENT_INFO_PATH, "r") as file:
        human_agent_info = file.read()
    hooks.log(
        f"Human agent info provided at {HUMAN_AGENT_INFO_PATH}:\n\n {human_agent_info}"
    )

    hooks.log_with_attributes(
        {"style": {"background-color": "#bcd3d6"}},
        "Setup flag detected. Starting monitoring.",
    )

    jsonl_paths_to_monitor = [
        Path(CLOCK_JSONL_PATH),
        Path(NOTE_JSONL_PATH),
        Path(TERMINAL_JSONL_PATH),
    ]

    for path in jsonl_paths_to_monitor:
        path.touch()

    monitor_task = asyncio.create_task(monitors(jsonl_paths_to_monitor))

    try:
        while True:
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        monitor_task.cancel()
        await monitor_task


if __name__ == "__main__":
    hooks.main(main)
