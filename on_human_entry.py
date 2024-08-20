import os
import sys
import subprocess
from pathlib import Path
from util import NOTE_PY_PATH, CLOCK_PY_PATH, SUBMIT_PY_PATH, ON_HUMAN_ENTRY_PATH, HUMAN_AGENT_INFO_PATH, TERMINAL_PY_PATH, TERMINAL_LOG_PATH, TASK_TXT_PATH, SETUP_FLAG_PATH, use_hook, get_shell_config_path


def add_aliases():
    
    with open(get_shell_config_path(), "a") as f:
        """ Add aliases to the shell configuration file """
        aliases = [
            f"alias note!='python {NOTE_PY_PATH}'",
            f"alias clock!='python {CLOCK_PY_PATH}'",
            f"alias submit!='python {SUBMIT_PY_PATH}'"
            f"alias setup!='python {ON_HUMAN_ENTRY_PATH}'"
        ]
        for alias in aliases:
            f.write(alias + "\n")

def create_setup_flag():
    open(SETUP_FLAG_PATH, 'a').close()
    

def introduction():
    msg = f"""=======================================================
Welcome to the Headless-Human Agent!
=======================================================
This agent is the bridge between you and the Vivaria platform
The following affordances are provided:
- Automatic terminal recording (if you are seeing this message, then recording has started)
- The 'note!' command, which we encourage you to use to take stream-of-consciousness notes
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
    with open(HUMAN_AGENT_INFO_PATH, "w") as file:
        file.write(msg)
    use_hook("log", args=[f"Human agent info provided at {HUMAN_AGENT_INFO_PATH}:\n\n {msg}"])

def start_recording():
    # Start the script session
    Path(TERMINAL_LOG_PATH).touch() 
    subprocess.Popen(["python", TERMINAL_PY_PATH])
    subprocess.run(["asciinema", "rec", TERMINAL_LOG_PATH, "--overwrite", "-q"])

def main():
    add_aliases()
    create_setup_flag()
    introduction()
    start_recording()
    
    print("=======================================================")
    print("ATTENTION: RECORDING HAS STOPPED")
    print("=======================================================")
    print("PLEASE RUN 'setup!' TO RESTART THE RECORDING")
    print("=======================================================")

if __name__ == "__main__":
    main()
