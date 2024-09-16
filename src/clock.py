import asyncio
import enum
import json

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
LOG_ATTRIBUTES = {
    "style": {
        "background-color": "#f7b7c5",
        "border-color": "#d17b80",
    }
}


class ClockStatus(enum.Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"


def record_status(status: ClockStatus):
    entry = {"timestamp": get_timestamp(), "status": status.value}
    EVENTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(EVENTS_LOG, "a") as file:
        file.write(f"{json.dumps(entry)}\n")

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, "w") as file:
        file.write(status.value)


def get_status() -> ClockStatus:
    if not STATUS_FILE.exists():
        return ClockStatus.RUNNING

    with open(STATUS_FILE, "r") as file:
        return ClockStatus(file.read().strip())


async def pause(force: bool = False):
    if get_status() == ClockStatus.STOPPED and not force:
        return

    HOOKS.log_with_attributes(LOG_ATTRIBUTES, f"⏰ Clock paused at {get_timestamp()}")
    # Let the log call before pausing, otherwise error
    await asyncio.sleep(0.5)
    await HOOKS.pause()
    record_status(ClockStatus.STOPPED)


async def unpause(force: bool = False):
    if get_status() == ClockStatus.RUNNING and not force:
        return

    await HOOKS.unpause()
    HOOKS.log_with_attributes(LOG_ATTRIBUTES, f"⏰ Clock unpaused at {get_timestamp()}")
    record_status(ClockStatus.RUNNING)


async def main():
    clock_status = get_status()

    click.echo(f"Clock status: {clock_status.value}")
    click.echo(f"1. {'Stop' if clock_status == ClockStatus.RUNNING else 'Start'} clock")
    click.echo("2. Exit")
    try:
        choice = click.prompt("Enter your choice", type=click.Choice(["1", "2"]))

        if choice == "2":
            return

        if clock_status == ClockStatus.RUNNING:
            await pause()
            click.prompt(
                "Clock stopped. Press '1' to start clock",
                type=click.Choice(["1"]),
                show_choices=False,
            )

        await unpause()
        click.echo("Clock started.")
    except (click.exceptions.Abort, KeyboardInterrupt):
        click.echo(f"\nExiting, clock is {get_status().value}")

    await async_cleanup()


if __name__ == "__main__":
    asyncio.run(main())
