import datetime
import os
from util import hooks

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

def save_with_timestamp(text):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"note_{timestamp}.txt"
    
    # Create 'notes' directory if it doesn't exist
    script_dir = os.path.dirname(os.path.abspath(__file__))
    notes_dir = os.path.join(script_dir, 'notes')
    os.makedirs(notes_dir, exist_ok=True)
    
    # Full path for the output file
    file_path = os.path.join(notes_dir, filename)
    
    with open(file_path, "w") as file:
        file.write(f"--- Entry: {timestamp} ---\n")
        file.write(text)
        file.write("\n")
    
    hooks.log(text)
    
    return file_path

def main():
    while True:
        text = get_multiline_input()
        file_path = save_with_timestamp(text)
        print(f"\nYour input has been logged and saved to {file_path}")
        
        continue_input = input("Do you want to enter more text? (y/n): ").lower()
        if continue_input != 'y':
            break

if __name__ == "__main__":
    main()