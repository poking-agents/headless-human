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

# Add the aliases
echo "# Python script aliases" >> "$config_file"
echo "alias note!='python ~/.agent_code/note.py'" >> "$config_file"
echo "alias clock!='python ~/.agent_code/clock.py'" >> "$config_file"

# Reload the configuration
source "$config_file"

echo "Aliases have been added to $config_file"
echo "You can now use 'note!' and 'clock!' commands."