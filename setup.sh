#!/bin/bash

# Add aliases to .bashrc or .zshrc depending on the shell
if [ -n "$ZSH_VERSION" ]; then
    config_file="/home/agent/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    config_file="/home/agent/.bashrc"
else
    echo "Unsupported shell. Please add the aliases manually to your shell configuration file."
    exit 1
fi

# Load path environment variables
eval "$(python3 /home/agent/.agent_code/util.py)"
source "$config_file"

# Uncommenting the below will allow terminal gifs on other machines IFF the agent has internet access (will be fixed when agents can have non-python dependencies)

# if /home/agent/.agent_code/terminal_gifs.flag exists do this step, otherwise skip
# terminal_gifs_value=$(grep -o '"terminal_gifs":"[^"]*"' "settings.json" | sed 's/"terminal_gifs":"\(.*\)"/\1/')
# if [ "$terminal_gifs_value" == "TERMINAL_GIFS" ]; then
#     curl https://sh.rustup.rs -sSf | sh -s -- -y
#     source "$config_file"
#     . "$HOME/.cargo/env"   
#     cargo install --git https://github.com/asciinema/agg
# else
#     echo "Skipping installation of terminal gifs packages"
# fi

# Write the setup flag 
touch $SETUP_FLAG_PATH

# Add the aliases
echo "# Python script aliases" >> "$config_file"
echo "alias note!='python ~/.agent_code/note.py'" >> "$config_file"
echo "alias clock!='python ~/.agent_code/clock.py'" >> "$config_file"
echo "alias submit!='python ~/.agent_code/submit.py'" >> "$config_file"
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "$config_file"
echo "alias setup!='bash ~/.agent_code/setup.sh'" >> "$config_file" 

# Reload the configuration
source "$config_file"

# Introduction message
echo "======================================================="
echo "Welcome to the Headless-Human Agent!"
echo "======================================================="
echo "This agent is the bridge between you and the Vivaria platform"
echo "The following affordances are provided:"
echo "- Automatic terminal recording (if you are seeing this message, then recording has started)"
echo "- The 'note!' command, which we encourage you to use to take stream-of-consciousness notes"
echo "- The 'clock!' command, which allows you to start and pause the timer."
echo "- The 'submit!' command, which allows you to end your task and submit your work."
echo "======================================================="
echo "The above instructions will also be saved in the file $HUMAN_AGENT_INFO_PATH"
echo "======================================================="
echo "The clock is currently PAUSED."
echo "When you are ready to proceed, run 'clock!' and start the timer."
echo "Task instructions are at $TASK_TXT_PATH"
echo "======================================================="

# Save the instructions to a file
echo "=======================================================" > $HUMAN_AGENT_INFO_PATH
echo "Welcome to the Headless-Human Agent!" >> $HUMAN_AGENT_INFO_PATH
echo "=======================================================" >> $HUMAN_AGENT_INFO_PATH
echo "This agent is the bridge between you and the Vivaria platform" >> $HUMAN_AGENT_INFO_PATH
echo "The following affordances are provided:" >> $HUMAN_AGENT_INFO_PATH
echo "- Automatic terminal recording (if you are seeing this message, then recording has started)" >> $HUMAN_AGENT_INFO_PATH
echo "- The 'note!' command, which we encourage you to use to take stream-of-consciousness notes" >> $HUMAN_AGENT_INFO_PATH
echo "- The 'clock!' command, which allows you to start and pause the timer." >> $HUMAN_AGENT_INFO_PATH
echo "- The 'submit!' command, which allows you to end your task and submit your work." >> $HUMAN_AGENT_INFO_PATH
echo "=======================================================" >> $HUMAN_AGENT_INFO_PATH
echo "The above instructions will also be saved in the file $HUMAN_AGENT_INFO_PATH" >> $HUMAN_AGENT_INFO_PATH
echo "=======================================================" >> $HUMAN_AGENT_INFO_PATH
echo "The clock is currently PAUSED." >> $HUMAN_AGENT_INFO_PATH
echo "When you are ready to proceed, run 'clock!' and start the timer." >> $HUMAN_AGENT_INFO_PATH
echo "Task instructions are at $TASK_TXT_PATH" >> $HUMAN_AGENT_INFO_PATH
echo "=======================================================" >> $HUMAN_AGENT_INFO_PATH


# Start the script session
python $TERMINAL_PY_PATH &
JSONL_PID=$!
asciinema rec $TERMINAL_LOG_PATH --overwrite -q
# After the script session ends, terminate the background process
echo "Killing background terminal monitor process..."
kill $JSONL_PID


echo "======================================================="
echo "ATTENTION: RECORDING HAS STOPPED"
echo "======================================================="
echo "PLEASE RUN 'setup!' TO RESTART THE RECORDING"
echo "======================================================="