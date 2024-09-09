import json

import click
from src.util import AGENT_HOME_DIR, HOOKS, get_timestamp

LOG_FILE = AGENT_HOME_DIR / "notes.jsonl"
LOG_ATTRIBUTES = {
    "style": {
        "color": "#2b2928",
        "padding": "5px",
        "border-radius": "5px",
        "border-width": "thick",
        "background-color": "#f7e2c8",
        "border-color": "#d9b38e",
        "font-style": "italic",
    }
}


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

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as file:
        json.dump(entry, file)
        file.write("\n")


def main():
    text = get_multiline_input()
    append_to_jsonl(text)
    click.echo(f"Note added to {LOG_FILE}")
    HOOKS.log_with_attributes(LOG_ATTRIBUTES, text)


if __name__ == "__main__":
    main()
