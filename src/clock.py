import asyncio
import datetime
import enum
import json

import aiofiles
import click

from src.settings import (
    AGENT_CODE_DIR,
    AGENT_HOME_DIR,
    HOOKS,
    async_cleanup,
    get_timestamp,
)

EVENTS_LOG = AGENT_HOME_DIR / ".clock/log.jsonl"
STATUS_FILE = AGENT_CODE_DIR / ".clock/status.txt"
_LOG_ATTRIBUTES = {
    "style": {
        "background-color": "#f7b7c5",
        "border-color": "#d17b80",
    }
}


class ClockStatus(enum.Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"


async def record_status(status: ClockStatus):
    entry = {"timestamp": get_timestamp(), "status": status.value}
    EVENTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(EVENTS_LOG, "a") as file:
        await file.write(f"{json.dumps(entry)}\n")

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(STATUS_FILE, "w") as file:
        await file.write(status.value)


async def get_status() -> ClockStatus:
    if not STATUS_FILE.exists():
        return ClockStatus.RUNNING

    async with aiofiles.open(STATUS_FILE, "r") as file:
        return ClockStatus((await file.read()).strip())


async def get_time_elapsed() -> datetime.timedelta:
    time_elapsed = datetime.timedelta()
    if not EVENTS_LOG.exists():
        return time_elapsed

    start_time = None
    async with aiofiles.open(EVENTS_LOG, "r") as file:
        async for line in file:
            entry = json.loads(line)
            timestamp = datetime.datetime.fromisoformat(entry["timestamp"])

            status = ClockStatus(entry["status"])
            if status == ClockStatus.RUNNING and start_time is None:
                start_time = timestamp
            elif status == ClockStatus.STOPPED and start_time is not None:
                time_elapsed += timestamp - start_time
                start_time = None

    if start_time is not None:
        time_elapsed += datetime.datetime.now() - start_time

    time_elapsed -= datetime.timedelta(microseconds=time_elapsed.microseconds)
    return time_elapsed


async def pause(force: bool = False):
    if (await get_status()) == ClockStatus.STOPPED and not force:
        return

    await HOOKS.log_with_attributes(
        _LOG_ATTRIBUTES, f"⏰ Clock paused at {get_timestamp()}"
    )
    await HOOKS.pause()
    await record_status(ClockStatus.STOPPED)


async def unpause(force: bool = False):
    if (await get_status()) == ClockStatus.RUNNING and not force:
        return

    await HOOKS.unpause()
    await asyncio.gather(
        HOOKS.log_with_attributes(
            _LOG_ATTRIBUTES, f"⏰ Clock unpaused at {get_timestamp()}"
        ),
        record_status(ClockStatus.RUNNING),
    )


async def clock():
    clock_status, time_elapsed = await asyncio.gather(get_status(), get_time_elapsed())
    click.echo(f"Time elapsed: {time_elapsed}")
    click.echo(f"Clock status: {clock_status.value}")
    click.echo(f"1. {'Stop' if clock_status == ClockStatus.RUNNING else 'Start'} clock")
    click.echo("2. Exit")
    try:
        choice = click.prompt("Enter your choice", type=click.Choice(["1", "2"]))

        if choice == "2":
            return clock_status

        if clock_status == ClockStatus.RUNNING:
            await pause()
            clock_status = ClockStatus.STOPPED
            click.prompt(
                "Clock stopped. Press '1' to start clock",
                type=click.Choice(["1"]),
                show_choices=False,
            )

        await unpause()
        clock_status = ClockStatus.RUNNING
        click.echo("Clock started.")
    except (click.exceptions.Abort, KeyboardInterrupt):
        click.echo(f"\nExiting, clock is {clock_status.value}")

    return clock_status


async def main():
    await clock()
    await async_cleanup()


if __name__ == "__main__":
    asyncio.run(main())
