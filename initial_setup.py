import subprocess
import time
from pathlib import Path
from util import (
    use_hook,
    HUMAN_AGENT_INFO_PATH,
    INTERNAL_SETTINGS_JSON_PATH,
    TASK_TXT_PATH,
    NOTE_JSONL_PATH,
    ON_HUMAN_ENTRY_PATH,
)


def write_and_log_task_txt(task: dict) -> None:
    content = f"""Internet permissions for this task (where [] means no internet allowed). Permissions:{str(task.permissions)}

Task instructions: {task.instructions}"""
    with open(TASK_TXT_PATH, "w") as file:
        file.write(content)
    use_hook(
        "log_with_attributes",
        args=[
            {"style": {"background-color": "#bcd4ba"}},
            f"{TASK_TXT_PATH}:\n{content}",
        ],
    )


def agent_setup():
    use_hook("pause")
    task = use_hook("getTask")
    write_and_log_task_txt(task)

    Path(INTERNAL_SETTINGS_JSON_PATH).touch()
    subprocess.check_call(
        ["cp", "/home/agent/settings.json", INTERNAL_SETTINGS_JSON_PATH]
    )

    Path(NOTE_JSONL_PATH).touch()

    # Adds a line that auto runs setup on agent user login shells (i.e when human logs in with --user agent)
    subprocess.check_call(
        f'echo "bash {ON_HUMAN_ENTRY_PATH}" >> /home/agent/.profile',
        shell=True,
        check=True,
    )

    # Install agg
    # ONLY WORKS ON THE DEFAULT MACHINE (precompiled binary)
    # WILL FIX WHEN AGENTS CAN HAVE NON-PYTHON DEPENDENCIES
    subprocess.check_call(["chmod", "+x", ".agent_code/agg"])
    subprocess.check_call(["cp", ".agent_code/agg", "/home/agent/.local/bin/agg"])

    with open(HUMAN_AGENT_INFO_PATH, "r") as file:
        human_agent_info = file.read()
    use_hook(
        "log",
        args=[
            f"Human agent info provided at {HUMAN_AGENT_INFO_PATH}:\n\n {human_agent_info}"
        ],
    )


if __name__ == "__main__":
    agent_setup()
