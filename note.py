import datetime
import os
import json
from util import hooks, set_human_env_vars

def get_multiline_input():
    print("Enter your multiline text (press Ctrl+D or Ctrl+Z on a new line to finish):")
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass
    return '\n'.join(lines)

def append_to_jsonl(text):
    timestamp = datetime.datetime.now().isoformat()
    entry = {
        "timestamp": timestamp,
        "content": text
    }
    
    # Get the directory of the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Full path for the output file
    file_path = os.path.join(script_dir, "notes.jsonl")
    
    with open(file_path, "a") as file:
        json.dump(entry, file)
        file.write("\n")
    
    hooks.log(text)
    
    return file_path

def main():
    set_human_env_vars()
    while True:
        text = get_multiline_input()
        file_path = append_to_jsonl(text)
        print(f"\nYour input has been logged and appended to {file_path}")
        
        continue_input = input("Do you want to enter more text? (y/n): ").lower()
        if continue_input != 'y':
            break

if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e: # Runtime errors due to no agent main loop?
        pass