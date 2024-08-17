import os
import subprocess
from util import NOTE_PY_PATH, CLOCK_PY_PATH, SUBMIT_PY_PATH, ON_HUMAN_ENTRY_PATH, HUMAN_AGENT_INFO_PATH, TERMINAL_PY_PATH, TERMINAL_LOG_PATH, TASK_TXT_PATH, call_tool

def get_config_file():
    home = os.path.expanduser("~")
    if 'ZSH_VERSION' in os.environ:
        return os.path.join(home, ".zshrc")
    elif 'BASH_VERSION' in os.environ:
        return os.path.join(home, ".bashrc")
    else:
        print("Unsupported shell. Please add the aliases manually to your shell configuration file.")
        exit(1)

def add_aliases(config_file):
    
    with open(config_file, "a") as f:
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
    setup_flag_path = os.environ.get('SETUP_FLAG_PATH')
    open(setup_flag_path, 'a').close()
    

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
    call_tool("log", args=[f"Human agent info provided at {HUMAN_AGENT_INFO_PATH}:\n\n {msg}"])

def start_recording():
    # Start the script session
    subprocess.Popen(["python", TERMINAL_PY_PATH])
    subprocess.run(["asciinema", "rec", TERMINAL_LOG_PATH, "--overwrite", "-q"])

def main():
    config_file = get_config_file()
    add_aliases(config_file)
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
