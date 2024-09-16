from __future__ import annotations

import asyncio
import enum
import json
import os
import pathlib
import sys
import textwrap

import click

import src.clock as clock
from src.settings import (
    AGENT_CODE_DIR,
    AGENT_HOME_DIR,
    HOOKS,
    INSTRUCTIONS_FILE,
    RUN_INFO_FILE,
    async_cleanup,
)

AGENT_PROFILE_FILE = AGENT_CODE_DIR / "profile.sh"
WELCOME_MESSAGE_FILE = AGENT_HOME_DIR / "welcome.txt"


class HelperCommand(enum.Enum):
    mclock = "clock.py"
    mnote = "note.py"
    mrecord = "terminal.py"
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


def _get_shell_config_file(shell_path: pathlib.Path):
    shell_config_files = {
        "zsh": ".zshrc",
        "bash": ".bashrc",
        "fish": ".config/fish/config.fish",
    }
    # Remove version numbers if present (e.g., zsh-5.8)
    shell_name = shell_path.name.lower().split("-")[0]

    # Special case for Python shells
    if "python" in shell_name:
        return None
    elif shell_name not in shell_config_files:
        raise RuntimeError(
            f"Configuration file for {shell_name} not found or shell could not be determined."
        )

    return pathlib.Path.home() / shell_config_files[shell_name]


def _get_welcome_message(
    commands: dict[str, str], instructions: str
) -> tuple[str, str]:
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
    Task instructions are at {instructions_file}, and are also displayed below.
    =================================================================================
    {instructions}
    """

    commands_text = "\n".join(
        [f"- `{command}`: {description}" for command, description in commands.items()]
    )
    welcome_saved = (
        textwrap.dedent(welcome_saved).format(commands_text=commands_text).strip()
    )
    welcome_unsaved = (
        textwrap.dedent(welcome_unsaved)
        .format(
            clock_status=clock_status.value,
            instructions_file=INSTRUCTIONS_FILE,
            instructions=instructions,
            welcome_message_file=WELCOME_MESSAGE_FILE,
        )
        .lstrip()
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
    intermediate_scoring: bool = False,
    with_recording: bool = True,
    env: dict[str, str],
    profile_file: pathlib.Path = AGENT_PROFILE_FILE,
):
    profile_file.parent.mkdir(parents=True, exist_ok=True)
    profile = """
    {aliases}
    {exports}
    [ -z "${{METR_BASELINE_SETUP_COMPLETE}}" ] && {setup_command} && export METR_BASELINE_SETUP_COMPLETE=1
    {recording_command}
    """
    with profile_file.open("w") as f:
        f.write(
            textwrap.dedent(profile)
            .lstrip()
            .format(
                aliases="\n".join(
                    [
                        f"alias {command.name}='PYTHONPATH={AGENT_CODE_DIR} python {AGENT_CODE_DIR}/src/{command.value}'"
                        for command in HelperCommand
                        if not (
                            command in {HelperCommand.mscore, HelperCommand.mscore_log}
                            and not intermediate_scoring
                        )
                        and not (
                            command == HelperCommand.mrecord and not with_recording
                        )
                    ]
                ),
                exports="\n".join(
                    [
                        *(f"export {key}='{value}'" for key, value in env.items()),
                        "export SHELL",
                    ]
                ),
                setup_command=HelperCommand.msetup.name,
                recording_command=(
                    " && ".join(
                        [
                            "[ -z ${METR_RECORDING_STARTED} ]",
                            f"PYTHONPATH={AGENT_CODE_DIR} python {AGENT_CODE_DIR}/src/{HelperCommand.mrecord.value}",
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
            return True
        f.write(f". {profile_file}\n")
    return False


async def main():
    run_info = json.loads(RUN_INFO_FILE.read_text())
    welcome_saved, _ = introduction(run_info)
    if not WELCOME_MESSAGE_FILE.exists():
        WELCOME_MESSAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        WELCOME_MESSAGE_FILE.write_text(welcome_saved)
        if clock.get_status() == clock.ClockStatus.RUNNING:
            HOOKS.log(
                f"Human agent info provided at {WELCOME_MESSAGE_FILE}:\n\n{welcome_saved}"
            )

    try:
        shell_path = _get_shell_path()
    except RuntimeError:
        click.echo(
            "Could not determine shell path, skipping profile file sourcing", err=True
        )
        return

    shell_config_file = _get_shell_config_file(shell_path)
    if shell_config_file is None:
        return

    os.environ["METR_BASELINE_SETUP_COMPLETE"] = "1"
    process = await asyncio.create_subprocess_exec(
        str(shell_path),
        "--login",
        "-i",
        "-c",
        f"type {HelperCommand.mclock.name}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env={**os.environ, "METR_RECORDING_STARTED": "1"},
    )
    await process.wait()
    is_alias_defined = process.returncode == 0
    if not is_alias_defined:
        ensure_sourced(shell_config_file, AGENT_PROFILE_FILE)
        click.echo(
            "Please run the following commands to complete the setup and start the task:"
        )
        click.echo(f"\n  source {shell_config_file}")
        click.echo(f"  {HelperCommand.mclock.name}")
    elif clock.get_status() == clock.ClockStatus.STOPPED:
        await clock.main()

    await async_cleanup()


if __name__ == "__main__":
    asyncio.run(main())
