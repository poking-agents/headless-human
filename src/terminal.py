from __future__ import annotations

import asyncio
import base64
import fcntl
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import click

import src.clock as clock
from src.settings import (
    AGENT_CODE_DIR,
    HOOKS,
    INTERNAL_SUBMISSION_PATH,
    get_settings,
    get_task_env,
)

if TYPE_CHECKING:
    from _typeshed import StrPath

    TerminalEvent = tuple[float, str, str]

LOG_ATTRIBUTES = {
    "style": {
        "color": "white",
        "background-color": "#424345",
    }
}
_LOG_DIR = AGENT_CODE_DIR / ".terminals"
_WINDOW_IDS_FILE = _LOG_DIR / "window_ids.json"


def file_to_base64(file_path: StrPath) -> str:
    extension = pathlib.Path(file_path).suffix
    image_base64 = base64.b64encode(open(file_path, "rb").read()).decode("utf-8")
    image_base64_formatted = f"data:image/{extension[1:]};base64," + image_base64
    return image_base64_formatted


def strip_ansi(text: str) -> str:
    ansi_escape = re.compile(
        r"""
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
""",
        re.VERBOSE,
    )
    return ansi_escape.sub("", text)


def get_time_from_last_entry_of_cast(cast_file: StrPath) -> float:
    with open(cast_file, "r") as f:
        lines = f.readlines()
        last_line = next(line for line in reversed(lines) if line.strip())
        last_entry = json.loads(last_line)
        return last_entry[0]


def load_cast_file(
    cast_file: StrPath, start_position: int = 0
) -> tuple[dict | None, list[TerminalEvent], int]:
    events: list[TerminalEvent] = []
    current_position = start_position
    with open(cast_file, "r") as f:
        f.seek(start_position)
        if start_position == 0:
            header = json.loads(f.readline())
            current_position = f.tell()
        else:
            header = None

        events = [json.loads(line) for line in f if line.strip()]
        current_position = f.tell()
        return header, events, current_position


def cast_to_string(events: list[TerminalEvent]) -> str:
    string = "".join([event[2] for event in events])
    return string


def has_events_with_string(
    events: list[TerminalEvent], string: str, number: int
) -> bool:
    events_with_string = [event for event in events if string in event[2]]
    return len(events_with_string) >= number


def adjust_event_times(
    events: list[TerminalEvent], time_offset: float
) -> list[TerminalEvent]:
    time_offset_events = [
        (
            round(event[0] - time_offset, 6),
            event[1],
            event[2],
        )
        for event in events
    ]
    return time_offset_events


class LogMonitor:
    def __init__(
        self,
        window_id: int,
        terminal_gifs: bool | None = None,
        log_dir: pathlib.Path = _LOG_DIR,
        fps_cap: int = 7,
        speed: float = 3,
    ):
        self.window_id = window_id
        self.log_dir = log_dir / str(window_id)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        if terminal_gifs is None:
            terminal_gifs = get_settings()["agent"]["terminal_recording"] in {
                "GIF_TERMINAL_RECORDING",
                "FULL_TERMINAL_RECORDING",
            }
        self.terminal_gifs = terminal_gifs

        self.last_position = 0
        self.last_update = 0
        self.last_cast_time = 0
        self.last_hooks_log_time = 0
        self.fps_cap = fps_cap
        self.speed = speed
        self.cast_header = None
        self.terminal_log_buffer = ""
        self.terminal_prefix = None

    @property
    def log_file(self) -> pathlib.Path:
        return self.log_dir / "terminal.cast"

    @property
    def trimmed_log_file(self) -> pathlib.Path:
        return self.log_dir / "trimmed_terminal.cast"

    @property
    def gif_file(self) -> pathlib.Path:
        return self.log_dir / "terminal.gif"

    async def run(self):
        try:
            while True:
                if clock.get_status() == clock.ClockStatus.RUNNING:
                    await self.check_for_updates()
                await asyncio.sleep(0.5)
        except KeyboardInterrupt:
            click.echo("Monitoring stopped.")

    async def check_for_updates(self):
        if (
            not self.log_file.exists()
            or self.log_file.stat().st_mtime + 1 <= self.last_update
        ):
            return

        try:
            await self.update_jsonl()
        except Exception as error:
            click.echo(f"Error updating JSONL: {error!r}")
            if isinstance(error, subprocess.CalledProcessError):
                click.echo(error.output)

        self.last_update = time.time()

    async def update_jsonl(self):
        cast_header, new_events, current_position = load_cast_file(
            self.log_file, self.last_position
        )
        if cast_header:
            self.cast_header = cast_header
        if not new_events:
            return
        if self.terminal_prefix is None:
            self.terminal_prefix = new_events[0][-1].strip()

        if not (
            has_events_with_string(new_events, self.terminal_prefix, 2)
            or (INTERNAL_SUBMISSION_PATH / "terminals" / self.log_dir.name).exists()
        ):
            return

        new_cast_time = get_time_from_last_entry_of_cast(self.log_file)
        time_offset_events = adjust_event_times(new_events, self.last_cast_time)
        self.last_cast_time = new_cast_time
        self.last_position = current_position

        # Write to the trimmed terminal cast file, writing the header and then the time offset events
        self.last_hooks_log_time = time.time()
        with open(self.trimmed_log_file, "w") as f:
            if self.cast_header:
                json.dump(self.cast_header, f)
                f.write("\n")
            for event in time_offset_events:
                json.dump(event, f)
                f.write("\n")

        formatted_entry = cast_to_string(new_events)
        formatted_entry = strip_ansi(formatted_entry)
        formatted_entry = f"Terminal window: {self.window_id}\n\n{formatted_entry}"
        HOOKS.log_with_attributes(LOG_ATTRIBUTES, formatted_entry)

        if not self.terminal_gifs:
            return

        await asyncio.sleep(0.1)
        args = [
            "agg",
            self.trimmed_log_file,
            self.gif_file,
            "--fps-cap",
            str(self.fps_cap),
            "--speed",
            str(self.speed),
            "--idle-time-limit",
            "1",
            "--last-frame-duration",
            "5",
        ]
        process = await asyncio.subprocess.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode,
                args,
                output=(await process.stdout.read()).decode(),
            )
        HOOKS.log_image(file_to_base64(self.gif_file))


async def start_recording(
    window_id: int, log_dir: pathlib.Path, fps_cap: int, speed: float
):
    envs_to_preserve = ["SHELL", "TERM", *get_task_env()]
    monitor = LogMonitor(
        window_id=window_id,
        log_dir=log_dir,
        fps_cap=fps_cap,
        speed=speed,
    )
    try:
        monitor_task = asyncio.create_task(monitor.run())
        record_process = await asyncio.subprocess.create_subprocess_exec(
            sys.executable,
            "-m",
            "asciinema",
            "rec",
            "--overwrite",
            "--quiet",
            f"--env={','.join(envs_to_preserve)}",
            f"--command={os.environ['SHELL']}",
            log_dir / f"{window_id}/terminal.cast",
            env=os.environ,
        )
        await record_process.wait()
    except subprocess.CalledProcessError as error:
        click.echo(f"Error recording terminal: {error!r}")
    finally:
        if not monitor_task.done():
            monitor_task.cancel()


@click.command()
@click.option(
    "--log_dir",
    type=click.Path(file_okay=False, writable=True, path_type=pathlib.Path),
    default=_LOG_DIR,
)
@click.option("--fps_cap", type=int, default=7)
@click.option("--speed", type=float, default=3)
def main(log_dir: pathlib.Path, fps_cap: int, speed: float):
    _WINDOW_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(f"{_WINDOW_IDS_FILE}.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        if _WINDOW_IDS_FILE.exists():
            existing_ids = json.loads(_WINDOW_IDS_FILE.read_text())
        else:
            existing_ids = []
        window_id = max(existing_ids) if existing_ids else 0
        existing_ids.append(window_id)
        _WINDOW_IDS_FILE.write_text(json.dumps(existing_ids))

    try:
        asyncio.run(start_recording(window_id, log_dir, fps_cap, speed))
    finally:
        click.echo("=======================================================")
        click.echo("ATTENTION: TERMINAL RECORDING HAS STOPPED")
        click.echo("=======================================================")
        click.echo("PLEASE RUN 'mrecord' TO RESTART THE RECORDING")
        click.echo("=======================================================")


if __name__ == "__main__":
    main()
