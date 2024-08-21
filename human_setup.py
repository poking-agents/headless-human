import json
import subprocess
import os
import sys
from pathlib import Path
from util import NOTE_PY_PATH, CLOCK_PY_PATH, SUBMIT_PY_PATH, ON_HUMAN_ENTRY_PATH, HUMAN_AGENT_INFO_PATH, TERMINAL_PY_PATH, TERMINAL_LOG_PATH, TASK_TXT_PATH, NOTE_JSONL_PATH, TERMINAL_WINDOW_IDS_JSON, SETUP_FLAG_PATH, use_hook, READ_THIS_FIRST_PATH, get_shell_config_path, local_mode


def add_aliases():
    
    with open(get_shell_config_path(), "a") as f:
        """ Add aliases to the shell configuration file """
        aliases = [
            f"alias note!='python {NOTE_PY_PATH}'",
            f"alias clock!='python {CLOCK_PY_PATH}'",
            f"alias submit!='python {SUBMIT_PY_PATH}'",
            f"alias setup!='python {ON_HUMAN_ENTRY_PATH}'"
        ]
        for alias in aliases:
            f.write(alias + "\n")

def create_setup_flag():
    open(SETUP_FLAG_PATH, 'a').close()

def is_first_time() -> bool:
    if Path(SETUP_FLAG_PATH).exists():
        return False
    return True

def introduction():
    msg = f"""=======================================================
Welcome to the Headless-Human Agent!
=======================================================
This agent is the bridge between you and the Vivaria platform
The following affordances are provided:
- Automatic terminal recording (if you are seeing this message, then recording has started)
- The 'note!' command, which we encourage you to use to take stream-of-consciousness notes. These will be saved in {NOTE_JSONL_PATH}
- The 'clock!' command, which allows you to start and pause the timer.
- The 'submit!' command, which allows you to end your task and submit your work.
=======================================================
The above instructions will also be saved in the file {HUMAN_AGENT_INFO_PATH} 
=======================================================
The clock is currently PAUSED.
When you are ready to proceed, run 'clock!' and start the timer.
Task instructions are at {TASK_TXT_PATH}
======================================================="""
    print(msg)
    with open(READ_THIS_FIRST_PATH, "r") as file:
        content = file.read()
    use_hook("log", args=[f"Human setup instructions provided at {READ_THIS_FIRST_PATH}:\n\n {content}"])
        
    with open(HUMAN_AGENT_INFO_PATH, "w") as file:
        file.write(msg)
    use_hook("log", args=[f"Human agent info provided at {HUMAN_AGENT_INFO_PATH}:\n\n {msg}"])
    

def start_recording():
    if not Path(TERMINAL_WINDOW_IDS_JSON).exists():
        with open(TERMINAL_WINDOW_IDS_JSON, "w") as f:
            f.write("[]")
    else:
        existing_ids = json.loads(Path(TERMINAL_WINDOW_IDS_JSON).read_text())
    max_id = max(existing_ids) if existing_ids else -1
    current_id = max_id + 1
    existing_ids.append(current_id)

    with open(TERMINAL_WINDOW_IDS_JSON, "w") as f:
        json.dump(existing_ids, f)    
    
    current_terminal_log_path = TERMINAL_LOG_PATH.replace(".cast", f"_{current_id}.cast")
    Path(current_terminal_log_path).touch()
    
    subprocess.Popen(["python", TERMINAL_PY_PATH, "--window_id", str(current_id), "--log_path", current_terminal_log_path])
    current_env = os.environ.copy()
    subprocess.run([sys.executable,"-m","asciinema", "rec", current_terminal_log_path, "--overwrite", "-q"], env = current_env)

def main():
    if not local_mode:
        add_aliases()
    if is_first_time():
        create_setup_flag()
        introduction()
    start_recording()
    
    print("=======================================================")
    print("ATTENTION: TERMINAL RECORDING HAS STOPPED")
    print("=======================================================")
    print("PLEASE RUN 'setup!' TO RESTART THE RECORDING")
    print("=======================================================")

if __name__ == "__main__":
    main()
