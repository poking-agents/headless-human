from __future__ import annotations

import enum
import json
import os
import pathlib
import subprocess
import sys
import textwrap

import click
import src.clock as clock
from src.util import (
    AGENT_CODE_DIR,
    AGENT_HOME_DIR,
    HOOKS,
    INSTRUCTIONS_FILE,
    RUN_INFO_FILE,
)

AGENT_PROFILE_FILE = AGENT_CODE_DIR / "profile.sh"
WELCOME_MESSAGE_FILE = AGENT_HOME_DIR / "welcome.txt"


class HelperCommand(enum.Enum):
    mclock = "clock.py"
    mnote = "note.py"
    mscore = "score.py score"
    mscore_log = "score.py log"
    msetup = "human_setup.py"
    msubmit = "submit.py"


def _get_shell_path():
    """Get the shell that the human is using"""
    # Method 1: Check SHELL environment variable
    shell_path = os.environ.get("SHELL", "")
    if shell_path:
        return pathlib.Path(shell_path)

    # Method 2: Check parent process name (works in most Unix-like systems)
    if hasattr(os, "getppid"):
        try:
            with open(f"/proc/{os.getppid()}/comm", "r") as f:
                return pathlib.Path(f.read().strip())
        except FileNotFoundError:
            pass  # /proc not available, skip this method

    # Method 3: Check sys.executable for Python shells like IPython
    if "python" in sys.executable:
        return pathlib.Path(sys.executable)

    raise RuntimeError("Could not determine shell path")


def _get_shell_config_file():
    # Dictionary mapping shell names to their config files
    config_files = {
        "zsh": ".zshrc",
        "bash": ".bashrc",
        "fish": ".config/fish/config.fish",
    }

    home_dir = pathlib.Path.home()
    shell_name = _get_shell_path().name.lower()
    # Remove version numbers if present (e.g., zsh-5.8)
    shell_name = shell_name.split("-")[0]

    # Special case for Python shells
    if "python" in shell_name:
        return None
    elif shell_name not in config_files:
        raise RuntimeError(
            f"Configuration file for {shell_name} not found or shell could not be determined."
        )

    return home_dir / config_files[shell_name]


def _setup_shell_profile():
    config_file = _get_shell_config_file()
    if config_file is None:
        return

    with config_file.open("r+") as f:
        if f.read().find(str(AGENT_PROFILE_FILE)) != -1:
            return
        f.write(f". {AGENT_PROFILE_FILE}\n")

    return config_file


def _get_welcome_message(commands: dict[str, str], instructions: str) -> tuple[str, str]:
    clock_status = clock.get_status()

    welcome_saved = """
    =================================================================================
                            WELCOME TO YOUR METR TASK!
    =================================================================================
    Please use the following commands as you complete your work:
    {commands_text}
    =================================================================================
    """

    welcome_unsaved = """
    The above instructions will also be saved in the file {welcome_message_file} 
    =================================================================================
    The clock is currently {clock_status}. When you are ready to proceed, run
    `mclock` to start the timer.
    Task instructions are at {instructions_file}, and are also displayed below.
    =================================================================================
    {instructions}
    """

    commands_text = "\n".join(
        [f"- `{command}`: {description}" for command, description in commands.items()]
    )
    welcome_saved = textwrap.dedent(welcome_saved).format(commands_text=commands_text).strip()
    welcome_unsaved = (
        textwrap.dedent(welcome_unsaved)
        .format(
            clock_status=clock_status,
            instructions_file=INSTRUCTIONS_FILE,
            instructions=instructions,
            welcome_message_file=WELCOME_MESSAGE_FILE,
        )
        .strip()
    )

    return welcome_saved, welcome_unsaved


def introduction(run_info: dict):
    commands = {
        HelperCommand.mclock.name: "Start and pause the timer.",
        HelperCommand.mnote.name: "Take stream-of-consciousness notes, which we highly encourage!",
        HelperCommand.msubmit.name: "End your task and submit your work.",
    }
    if run_info["task"]["scoring"]["intermediate"]:
        commands.update(
            {
                HelperCommand.mscore.name: "Score your current work without ending the task.",
                HelperCommand.mscore_log.name: "Get the history of results of running score!.",
            }
        )

    welcome_saved, welcome_unsaved = _get_welcome_message(
        commands, run_info["task"]["instructions"]
    )
    click.echo(welcome_saved)
    click.echo(welcome_unsaved)
    return welcome_saved, welcome_unsaved


def create_profile_file(
    *,
    with_recording: bool = True,
    env: dict[str, str],
    profile_file: pathlib.Path = AGENT_PROFILE_FILE,
):
    profile_file.parent.mkdir(parents=True, exist_ok=True)
    profile = """
    {aliases}
    {exports}
    [ -z "${{METR_BASELINE_SETUP_RUN}}" ] && {setup_command} && export METR_BASELINE_SETUP_RUN=1
    {recording_command}
    """
    with profile_file.open("w") as f:
        f.write(
            textwrap.dedent(profile)
            .lstrip()
            .format(
                aliases="\n".join(
                    [
                        f"alias {command.name}='python {AGENT_CODE_DIR / command.value}'"
                        for command in HelperCommand
                    ]
                ),
                exports="\n".join([f"export {key}='{value}'" for key, value in env.items()]),
                setup_command=HelperCommand.msetup.name,
                recording_command=(
                    " && ".join(
                        [
                            "[ -z ${METR_RECORDING_STARTED} ]",
                            f"python {AGENT_CODE_DIR}/terminal.py",
                            "export METR_RECORDING_STARTED=1",
                        ]
                    )
                    if with_recording
                    else ""
                ),
            )
        )
    return profile_file


def ensure_sourced(shell_config_file: pathlib.Path, profile_file: pathlib.Path):
    shell_config_file.parent.mkdir(parents=True, exist_ok=True)
    shell_config_file.touch()
    with shell_config_file.open("r+") as f:
        if f.read().find(str(profile_file)) != -1:
            return
        f.write(f". {profile_file}\n")


def main():
    run_info = json.loads(RUN_INFO_FILE.read_text())
    welcome_saved, _ = introduction(run_info)
    if not WELCOME_MESSAGE_FILE.exists():
        WELCOME_MESSAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        WELCOME_MESSAGE_FILE.write_text(welcome_saved)
        if clock.get_status() == clock.ClockStatus.RUNNING:
            HOOKS.log(f"Human agent info provided at {WELCOME_MESSAGE_FILE}:\n\n{welcome_saved}")

    if (
        subprocess.run(
            ["type", HelperCommand.msetup.name], capture_output=True, check=False
        ).returncode
        == 0
    ):
        return

    shell_config_file = _setup_shell_profile()
    if shell_config_file is None:
        return

    ensure_sourced(shell_config_file, AGENT_PROFILE_FILE)
    click.echo("Please run the following command to complete the setup")
    click.echo(f"\n  source {shell_config_file}")


if __name__ == "__main__":
    main()
