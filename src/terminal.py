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
import traceback
from typing import TYPE_CHECKING

import aiofiles
import click

import src.clock as clock
from src.settings import (
    AGENT_CODE_DIR,
    HOOKS,
    async_cleanup,
    get_settings,
    get_task_env,
)

if TYPE_CHECKING:
    from _typeshed import StrPath

    TerminalEvent = tuple[float, str, str]

_LOG_ATTRIBUTES = {
    "style": {
        "color": "white",
        "background-color": "#424345",
    }
}
_LOG_DIR = AGENT_CODE_DIR / ".terminals"
_WINDOW_IDS_FILE = _LOG_DIR / "window_ids.json"
_WINDOW_IDS_LOCK_FILE = _LOG_DIR / "window_ids.lock"


async def file_to_base64(file_path: StrPath) -> str:
    extension = pathlib.Path(file_path).suffix
    async with aiofiles.open(file_path, "rb") as f:
        image_base64 = base64.b64encode(await f.read()).decode("utf-8")
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


async def get_time_from_last_entry_of_cast(cast_file: StrPath) -> float:
    async with aiofiles.open(cast_file, "r") as f:
        lines = await f.readlines()
        last_line = next(line for line in reversed(lines) if line.strip())
        last_entry = json.loads(last_line)
        return last_entry[0]


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
        log_gifs: bool | None = None,
        log_text: bool | None = None,
        log_dir: pathlib.Path = _LOG_DIR,
        prompt_buffer: int = 5,
        fps_cap: int = 7,
        speed: float = 3,
    ):
        self.window_id = window_id
        self.log_dir = log_dir / str(window_id)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        if log_gifs is None:
            log_gifs = get_settings()["agent"]["terminal_recording"] in {
                "GIF_TERMINAL_RECORDING",
                "FULL_TERMINAL_RECORDING",
            }
        self.log_gifs = log_gifs
        if log_text is None:
            log_text = get_settings()["agent"]["terminal_recording"] in {
                "TEXT_TERMINAL_RECORDING",
                "FULL_TERMINAL_RECORDING",
            }

        self.log_text = log_text

        self.last_position = 0
        self.last_update = 0
        self.last_cast_time = 0
        self.last_hooks_log_time = 0
        self.fps_cap = fps_cap
        self.speed = speed
        self.cast_header = None
        self.terminal_log_buffer = ""
        self.terminal_prefix = None
        self.prompt_buffer = prompt_buffer
        self.new_events: list[TerminalEvent] = []

    @property
    def log_file(self) -> pathlib.Path:
        return self.log_dir / "terminal.cast"

    @property
    def trimmed_log_file(self) -> pathlib.Path:
        return self.log_dir / "trimmed_terminal.cast"

    @property
    def gif_file(self) -> pathlib.Path:
        return self.log_dir / "terminal.gif"

    async def read_from_log_file(self) -> list[TerminalEvent]:
        events: list[TerminalEvent] = []
        async with aiofiles.open(self.log_file, "r") as f:
            await f.seek(self.last_position)
            if self.last_position == 0:
                self.cast_header = json.loads(await f.readline())

            async for line in f:
                if not line.strip():
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            self.last_position = await f.tell()

        if events and self.terminal_prefix is None:
            self.terminal_prefix = events[0][-1].strip().split(" ")[0]

        self.new_events.extend(events)
        return events

    async def run(self):
        try:
            while True:
                if (await clock.get_status()) == clock.ClockStatus.RUNNING:
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
            await self._update()
        except Exception as error:
            click.echo(f"Traceback: {traceback.format_exc()}")
            click.echo(f"Error updating terminal log: {error!r}")
            if isinstance(error, subprocess.CalledProcessError):
                click.echo(error.output)

        self.last_update = time.time()

    async def _send_text_log(self):
        if not self.new_events:
            return

        formatted_entry = cast_to_string(self.new_events)
        formatted_entry = strip_ansi(formatted_entry)
        formatted_entry = f"Terminal window: {self.window_id}\n\n{formatted_entry}"
        await HOOKS.log_with_attributes(_LOG_ATTRIBUTES, formatted_entry)

    async def _send_gif_log(self):
        args = [
            "agg",
            self.trimmed_log_file,
            self.gif_file,
            f"--fps-cap={self.fps_cap:d}",
            f"--speed={self.speed:f}",
            "--idle-time-limit=1",
            "--last-frame-duration=5",
        ]
        process = await asyncio.subprocess.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await process.communicate()
        return_code = await process.wait()
        if return_code != 0:
            raise subprocess.CalledProcessError(
                return_code,
                args,
                output=stdout.decode(),
            )
        image_url = await file_to_base64(self.gif_file)
        await HOOKS.log_image(image_url)

    async def _update(self):
        await self.read_from_log_file()
        if not (
            self.new_events
            and self.terminal_prefix is not None
            and has_events_with_string(
                self.new_events, self.terminal_prefix, self.prompt_buffer + 1
            )
        ):
            return

        # Find the index of the Nth prompt (we want to send everything up to but not including this)
        prompt_indices = [i for i, event in enumerate(self.new_events) if self.terminal_prefix in event[2]]
        if len(prompt_indices) < self.prompt_buffer:
            return

        nth_prompt_index = prompt_indices[self.prompt_buffer - 1]

        complete_events = self.new_events[:nth_prompt_index]
        remaining_events = self.new_events[nth_prompt_index:]

        new_cast_time = await get_time_from_last_entry_of_cast(self.log_file)
        time_offset_events = adjust_event_times(complete_events, self.last_cast_time)
        self.last_cast_time = new_cast_time

        # Write to the trimmed terminal cast file, writing the header and then the time offset events
        self.last_hooks_log_time = time.time()
        async with aiofiles.open(self.trimmed_log_file, "w") as f:
            if self.cast_header:
                await f.write(json.dumps(self.cast_header) + "\n")
            for event in time_offset_events:
                await f.write(json.dumps(event) + "\n")

        if self.log_text:
            await self._send_text_log()

        if self.log_gifs:
            await self._send_gif_log()

        # Keep the remaining events for next time
        self.new_events = remaining_events


async def start_recording(
    window_id: int, log_dir: pathlib.Path, fps_cap: int, speed: float
):
    recording_started = os.getenv("METR_RECORDING_STARTED", None)
    os.environ["METR_RECORDING_STARTED"] = "1"
    envs_to_preserve = ["SHELL", "TERM", *get_task_env()]

    monitor = LogMonitor(
        window_id=window_id,
        log_dir=log_dir,
        fps_cap=fps_cap,
        speed=speed,
    )
    monitor_task = asyncio.create_task(monitor.run())
    try:
        record_process = await asyncio.subprocess.create_subprocess_exec(
            sys.executable,
            "-m",
            "asciinema",
            "rec",
            "--overwrite",
            "--quiet",
            f"--env={','.join(envs_to_preserve)}",
            f"--command={os.environ['SHELL']} -l",
            log_dir / f"{window_id}/terminal.cast",
            env=os.environ,
        )
        await record_process.wait()
    except subprocess.CalledProcessError as error:
        click.echo(f"Error recording terminal: {error!r}")
    finally:
        if recording_started is not None:
            os.environ["METR_RECORDING_STARTED"] = recording_started

        if not monitor_task.done():
            monitor_task.cancel()
        await async_cleanup()


def _get_window_id():
    _WINDOW_IDS_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_WINDOW_IDS_LOCK_FILE, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)

        if _WINDOW_IDS_FILE.exists():
            existing_ids = json.loads(_WINDOW_IDS_FILE.read_text())
        else:
            existing_ids = []
        window_id = max(existing_ids or [-1]) + 1
        existing_ids.append(window_id)
        _WINDOW_IDS_FILE.write_text(json.dumps(existing_ids))

        fcntl.flock(f, fcntl.LOCK_UN)
    return window_id


@click.command()
@click.option(
    "--log_dir",
    type=click.Path(file_okay=False, writable=True, path_type=pathlib.Path),
    default=_LOG_DIR,
)
@click.option("--fps_cap", type=int, default=7)
@click.option("--speed", type=float, default=3)
def main(log_dir: pathlib.Path, fps_cap: int, speed: float):
    window_id = _get_window_id()
    try:
        asyncio.run(start_recording(window_id, log_dir, fps_cap, speed))
    finally:
        click.echo("=======================================================")
        click.echo("ATTENTION: TERMINAL RECORDING HAS STOPPED")
        click.echo("=======================================================")
        click.echo("PLEASE RUN 'mrecord' TO RESTART THE RECORDING")
        click.echo("=======================================================")


if __name__ == "__main__" and os.getenv("METR_RECORDING_STARTED") != "1":
    main()
