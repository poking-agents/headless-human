import os
import sys
import subprocess
from pathlib import Path
from util import NOTE_PY_PATH, CLOCK_PY_PATH, SUBMIT_PY_PATH, ON_HUMAN_ENTRY_PATH, HUMAN_AGENT_INFO_PATH, TERMINAL_PY_PATH, TERMINAL_LOG_PATH, TASK_TXT_PATH, SETUP_FLAG_PATH, use_hook

def get_shell_config_path():
    # Dictionary mapping shell names to their config files
    config_files = {
        "zsh": ".zshrc",
        "bash": ".bashrc",
        "fish": ".config/fish/config.fish"
    }

    # Get the user's home directory
    home_dir = os.path.expanduser("~")

    # Method 1: Check SHELL environment variable
    shell_path = os.environ.get("SHELL", "")
    
    # Method 2: Check parent process name (works in most Unix-like systems)
    if not shell_path and hasattr(os, 'getppid'):
        try:
            with open(f"/proc/{os.getppid()}/comm", "r") as f:
                shell_path = f.read().strip()
        except FileNotFoundError:
            pass  # /proc not available, skip this method

    # Method 3: Check sys.executable for Python shells like IPython
    if not shell_path and "python" in sys.executable:
        shell_path = "python"

    # Extract shell name from the path
    shell_name = os.path.basename(shell_path).lower()

    # Remove version numbers if present (e.g., zsh-5.8)
    shell_name = shell_name.split('-')[0]

    # Special case for Python shells
    if shell_name == "python":
        return "Running in a Python environment. No specific shell config file."

    if shell_name in config_files:
        return str(os.path.join(home_dir, config_files[shell_name]))
    else:
        return f"Configuration file for {shell_name} not found or shell could not be determined."

def add_aliases(config_file):
    
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
    config_file = get_shell_config_path()
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
