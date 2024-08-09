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

# if /home/agent/.agent_code/terminal_gifs.flag exists do this step, otherwise skip
if [ -f /home/agent/.agent_code/terminal_gifs.flag ]; then
    curl https://sh.rustup.rs -sSf | sh -s -- -y
    source "$config_file"
    . "$HOME/.cargo/env"   
    cargo install --git https://github.com/asciinema/agg
else
    echo "Skipping installation of terminal gifs packages"
fi

# Write the setup flag 
touch /home/agent/.agent_code/setup.flag

# Add the aliases
echo "# Python script aliases" >> "$config_file"
echo "alias note!='python ~/.agent_code/note.py'" >> "$config_file"
echo "alias clock!='python ~/.agent_code/clock.py'" >> "$config_file"
echo "alias submit!='python ~/.agent_code/submit.py'" >> "$config_file"
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "$config_file"  

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
echo "The above instructions will also be saved in the file /home/agent/human_agent_info.txt"
echo "======================================================="
echo "The clock is currently PAUSED."
echo "When you are ready to proceed, run 'clock!' and start the timer."
echo "======================================================="

# Save the instructions to a file
echo "=======================================================" > /home/agent/human_agent_info.txt
echo "Welcome to the Headless-Human Agent!" >> /home/agent/human_agent_info.txt
echo "=======================================================" >> /home/agent/human_agent_info.txt
echo "This agent is the bridge between you and the Vivaria platform" >> /home/agent/human_agent_info.txt
echo "The following affordances are provided:" >> /home/agent/human_agent_info.txt
echo "- Automatic terminal recording (if you are seeing this message, then recording has started)" >> /home/agent/human_agent_info.txt
echo "- The 'note!' command, which we encourage you to use to take stream-of-consciousness notes" >> /home/agent/human_agent_info.txt
echo "- The 'clock!' command, which allows you to start and pause the timer." >> /home/agent/human_agent_info.txt
echo "- The 'submit!' command, which allows you to end your task and submit your work." >> /home/agent/human_agent_info.txt
echo "=======================================================" >> /home/agent/human_agent_info.txt
echo "The clock is currently PAUSED." >> /home/agent/human_agent_info.txt
echo "When you are ready to proceed, run 'clock!' and start the timer." >> /home/agent/human_agent_info.txt
echo "=======================================================" >> /home/agent/human_agent_info.txt


# Start the script session
python /home/agent/.agent_code/terminal.py &
JSONL_PID=$!
asciinema rec /home/agent/.agent_code/terminal.cast --overwrite -q
# After the script session ends, terminate the background process
echo "Killing background terminal monitor process..."
kill $JSONL_PID


echo "======================================================="
echo "ATTENTION: RECORDING HAS STOPPED"
echo "======================================================="
echo "PLEASE RUN source ~/.bashrc TO RESTART THE RECORDING"
echo "======================================================="