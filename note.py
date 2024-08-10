import json
from util import get_timestamp, NOTE_JSONL_PATH


def get_multiline_input():
    print("Enter your multiline note (press Ctrl+D on a new line to finish):")
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines)


def append_to_jsonl(text, file_path):
    entry = {"timestamp": get_timestamp(), "content": text}

    with open(file_path, "a") as file:
        json.dump(entry, file)
        file.write("\n")

    return file_path


def main():
    file_path = NOTE_JSONL_PATH
    while True:
        text = get_multiline_input()
        file_path = append_to_jsonl(text, file_path)
        print(f"\nYour input has been logged and appended to {file_path}")

        continue_input = input("Do you want to enter more text? (y/n): ").lower()
        if continue_input != "y":
            break


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:  # Runtime errors due to no agent main loop?
        pass
