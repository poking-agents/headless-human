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

curl https://sh.rustup.rs -sSf | sh -s -- -y
source "$config_file"
. "$HOME/.cargo/env"   
cargo install --git https://github.com/asciinema/agg

# Add the aliases
echo "# Python script aliases" >> "$config_file"
echo "alias note!='python ~/.agent_code/note.py'" >> "$config_file"
echo "alias clock!='python ~/.agent_code/clock.py'" >> "$config_file"
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "$config_file"

# Reload the configuration
source "$config_file"

echo "Aliases have been added to $config_file"
echo "You can now use 'note!' and 'clock!' commands."

# Start the script session
echo "Starting script session. Type 'exit' when you're done."
asciinema rec /home/agent/.agent_code/terminal.cast --overwrite -q

python /home/agent/.agent_code/terminal.py &
# Capture the PID of the background process
JSONL_PID=$!

# After the script session ends, terminate the background process
echo "Terminating terminal.py process..."
kill $JSONL_PID

echo "Session ended. Log has been saved to mysession.log and converted to JSONL format."