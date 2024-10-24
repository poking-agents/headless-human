from __future__ import annotations

import asyncio
import enum
import json
import os
import pathlib
import sys
import textwrap

import aiofiles
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
    clock = "clock.py"
    note = "note.py"
    record = "terminal.py"
    score = "score.py score"
    score_log = "score.py log"
    setup = "human_setup.py"
    submit = "submit.py ''"

    def alias_def(self):
        command = [
            f"PYTHONPATH={AGENT_CODE_DIR}",
            sys.executable,
            AGENT_CODE_DIR / "src" / self.value,
        ]
        return f"alias {self.name}='{' '.join(map(str, command))}'"


async def _get_shell_path():
    """Get the shell that the human is using"""
    # Method 1: Check SHELL environment variable
    shell_path = os.environ.get("SHELL", "")
    if shell_path:
        return pathlib.Path(shell_path)

    # Method 2: Check parent process name (works in most Unix-like systems)
    if hasattr(os, "getppid"):
        try:
            async with aiofiles.open(f"/proc/{os.getppid()}/comm", "r") as f:
                return pathlib.Path(await f.read())
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
        # "fish": ".config/fish/config.fish", # TODO: Add fish support
    }
    # Remove version numbers if present (e.g., zsh-5.8)
    shell_name = shell_path.name.lower().split("-")[0]

    # Special case for Python shells
    if "python" in shell_name:
        return None
    elif shell_name not in shell_config_files:
        raise NotImplementedError(f"Cannot configure terminal for {shell_name}")

    return pathlib.Path.home() / shell_config_files[shell_name]


async def _get_welcome_message(
    commands: dict[str, str], instructions: str
) -> tuple[str, str]:
    clock_status = await clock.get_status()

    welcome_saved = """
    =================================================================================
                            WELCOME TO YOUR METR TASK!
    =================================================================================
    Please use the following commands as you complete your work:
    {commands_text}
    =================================================================================
    Please don't modify any files in the `~/.agent_code/` directory. Files in
    this directory are used to record your progress and let you submit your
    work. They are not useful to the task itself.
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


async def introduction(run_info: dict):
    commands = {
        HelperCommand.clock.name: "Start and pause the timer, or see elapsed time. If you reload or otherwise close your terminal, you will need to run this command again.",
        HelperCommand.submit.name: "End your task and submit your work.",
    }
    if run_info["task"]["scoring"]["intermediate"]:
        commands.update(
            {
                HelperCommand.score.name: "Score your currently saved work without ending the task.",
                HelperCommand.score_log.name: f"Get the history of results of running {HelperCommand.score.name}.",
            }
        )

    welcome_saved, welcome_unsaved = await _get_welcome_message(
        commands, run_info["task"]["instructions"]
    )
    click.echo(welcome_saved)
    click.echo(welcome_unsaved)
    return welcome_saved, welcome_unsaved


def get_conditional_run_command(env_var: str, setup_command: HelperCommand):
    return " && ".join(
        [
            f"[ -z ${{{env_var}}} ]",
            f"$(type -t {setup_command.name} > /dev/null)",
            setup_command.name,
            f"export {env_var}=1",
        ]
    )


async def create_profile_file(
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
    {setup_command}
    {recording_command}
    """
    async with aiofiles.open(profile_file, "w") as f:
        await f.write(
            textwrap.dedent(profile)
            .lstrip()
            .format(
                aliases="\n".join(
                    [
                        command.alias_def()
                        for command in HelperCommand
                        if not (
                            command in {HelperCommand.score, HelperCommand.score_log}
                            and not intermediate_scoring
                        )
                        and not (command == HelperCommand.record and not with_recording)
                    ]
                ),
                exports="\n".join(
                    [
                        *(f"export {key}='{value}'" for key, value in env.items()),
                        "export SHELL",
                    ]
                ),
                setup_command=get_conditional_run_command(
                    "METR_BASELINE_SETUP_COMPLETE", HelperCommand.setup
                ),
                recording_command=get_conditional_run_command(
                    "METR_RECORDING_STARTED", HelperCommand.record
                )
                if with_recording
                else "",
            )
        )
    return profile_file


async def ensure_sourced(shell_config_file: pathlib.Path, profile_file: pathlib.Path):
    shell_config_file.parent.mkdir(parents=True, exist_ok=True)
    shell_config_file.touch()
    async with aiofiles.open(shell_config_file, "r+") as f:
        if (await f.read()).find(str(profile_file)) != -1:
            return True
        await f.write(f"\n[[ $- == *i* ]] && . {profile_file}\n")
    return False


async def main():
    if os.getenv("METR_BASELINE_SETUP_COMPLETE") == "1":
        return 0

    async with aiofiles.open(RUN_INFO_FILE, "r") as f:
        run_info = json.loads(await f.read())
    (welcome_saved, _), clock_status = await asyncio.gather(
        introduction(run_info),
        clock.get_status(),
    )
    if not WELCOME_MESSAGE_FILE.exists():
        WELCOME_MESSAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(WELCOME_MESSAGE_FILE, "w") as f:
            await f.write(welcome_saved.strip() + "\n")

        if clock_status == clock.ClockStatus.RUNNING:
            await HOOKS.log(
                f"Human agent info provided at {WELCOME_MESSAGE_FILE}:\n\n{welcome_saved}"
            )

    try:
        shell_path = await _get_shell_path()
    except (NotImplementedError, RuntimeError):
        click.echo(
            "Could not determine shell path, skipping profile file sourcing",
            err=True,
        )
        return 1

    shell_config_file = _get_shell_config_file(shell_path)
    if shell_config_file is None:
        click.echo(
            "Could not determine shell config file, skipping profile file sourcing",
            err=True,
        )
        return 1

    os.environ["METR_BASELINE_SETUP_COMPLETE"] = "1"
    process = await asyncio.create_subprocess_exec(
        str(shell_path),
        "--login",
        "-i",
        "-c",
        f"type {HelperCommand.clock.name}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=os.environ | {"METR_RECORDING_STARTED": "1"},
    )
    await process.wait()
    is_alias_defined = process.returncode == 0
    exit_code = 0
    if not is_alias_defined:
        await ensure_sourced(shell_config_file, AGENT_PROFILE_FILE)
        click.echo(
            "Please run the following commands to complete the setup and start the task:"
        )
        click.echo(f"\n  source {shell_config_file}")
        click.echo(f"  {HelperCommand.clock.name}")
        exit_code = 1
    elif clock_status == clock.ClockStatus.STOPPED:
        clock_status = await clock.clock()
        if clock_status == clock.ClockStatus.STOPPED:
            exit_code = 1

    await async_cleanup()
    return exit_code


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
