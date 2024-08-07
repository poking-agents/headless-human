import datetime
import json
from util import hooks, AGENT_CODE_DIR 
from pathlib import Path

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

def append_to_jsonl(text, file_path):
    timestamp = datetime.datetime.now().isoformat()
    entry = {
        "timestamp": timestamp,
        "content": text
    }
    
    with open(file_path, "a") as file:
        json.dump(entry, file)
        file.write("\n")
    
    hooks.log(text)
    
    return file_path

def main():
    file_path = Path(__file__).parent  / f"{Path(__file__).stem}.jsonl"
    while True:
        text = get_multiline_input()
        file_path = append_to_jsonl(text, file_path)
        print(f"\nYour input has been logged and appended to {file_path}")
        
        continue_input = input("Do you want to enter more text? (y/n): ").lower()
        if continue_input != 'y':
            break

if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e: # Runtime errors due to no agent main loop?
        pass