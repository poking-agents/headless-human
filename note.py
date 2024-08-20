import json
from util import get_timestamp, NOTE_JSONL_PATH, use_hook, tool_log_styles


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


def append_to_jsonl(text):
    entry = {"timestamp": get_timestamp(), "content": text}

    with open(NOTE_JSONL_PATH, "a") as file:
        json.dump(entry, file)
        file.write("\n")


def main():
    text = get_multiline_input()
    append_to_jsonl(text)
    print(f"Note added to {NOTE_JSONL_PATH}")
    use_hook(
        "log_with_attributes",
        args=[tool_log_styles["note"], text],
    )

if __name__ == "__main__":
    main()
