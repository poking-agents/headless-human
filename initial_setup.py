import subprocess
import time
import requests
from pathlib import Path
from util import (
    use_hook,
    HUMAN_AGENT_INFO_PATH,
    INTERNAL_SETTINGS_JSON_PATH,
    NOTE_JSONL_PATH,
    SETTINGS_PATH,
    TASK_TXT_PATH,
    HOOK_SERVER_PORT,
    ON_HUMAN_ENTRY_PATH,
    HOME_AGENT_DIR,
    get_shell_config_path,
    local_mode,
)


def write_and_log_task_txt(task: dict) -> None:
    content = f"""Internet permissions for this task (where [] means no internet allowed). Permissions:{str(task["permissions"])}

Task instructions: {task["instructions"]}"""
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
    while True:
        try:
            output = requests.get(f"http://localhost:{HOOK_SERVER_PORT}/test")
            if output.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    print("Connected to hook server")
    task = use_hook("getTask")
    print(task)
    write_and_log_task_txt(task)

    Path(INTERNAL_SETTINGS_JSON_PATH).touch()
    subprocess.check_call(["cp", SETTINGS_PATH, INTERNAL_SETTINGS_JSON_PATH])

    Path(NOTE_JSONL_PATH).touch()

    if not local_mode:
        subprocess.check_call(
            f'echo "python {ON_HUMAN_ENTRY_PATH}" >> {HOME_AGENT_DIR}/.profile',
            shell=True,
        )
    
    # Install agg
    # ONLY WORKS ON THE DEFAULT MACHINE (precompiled binary)
    # WILL FIX WHEN AGENTS CAN HAVE NON-PYTHON DEPENDENCIES
    # subprocess.check_call(["chmod", "+x", ".agent_code/agg"])
    # subprocess.check_call(["cp", ".agent_code/agg", "/home/agent/.local/bin/agg"])

    use_hook("pause")


if __name__ == "__main__":
    agent_setup()
