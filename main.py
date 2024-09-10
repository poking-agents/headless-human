import asyncio
import json
import pathlib
import shutil
import textwrap

import click
import pyhooks
import src.clock as clock
import src.human_setup as human_setup
from src.util import (
    AGENT_CODE_DIR,
    AGENT_HOME_DIR,
    INSTRUCTIONS_FILE,
    RUN_INFO_FILE,
    get_task_env,
)

_SETUP_DONE_FILE = AGENT_CODE_DIR / ".done"

HOOKS = pyhooks.Hooks()


async def write_and_log_instructions(task_info: pyhooks.TaskInfo) -> None:
    instructions = """
    Internet permissions: {permissions}

    Task instructions:
    {instructions}
    """
    content = textwrap.dedent(instructions).format(
        permissions=", ".join(task_info.permissions or ["no internet"]),
        instructions=task_info.instructions,
    )

    INSTRUCTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    INSTRUCTIONS_FILE.write_text(content)

    HOOKS.log_with_attributes(
        {"style": {"background-color": "#bcd4ba"}},
        f"{INSTRUCTIONS_FILE}:\n{content}",
    )


async def setup():
    task_info = await HOOKS.getTask()
    await write_and_log_instructions(task_info)
    run_info = {
        "task": task_info.dict(),
        "agent": json.loads((AGENT_HOME_DIR / "settings.json").read_text()),
    }
    RUN_INFO_FILE.write_text(json.dumps(run_info))

    # TODO: replace with install as part of image build when agents can have
    # non-python dependencies
    destination = pathlib.Path.home() / ".local/bin/agg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(AGENT_CODE_DIR / "lib/agg", destination)

    return run_info


async def _main(reset: bool = False):
    if reset:
        _SETUP_DONE_FILE.unlink(missing_ok=True)
        clock.STATUS_FILE.unlink(missing_ok=True)
        human_setup.AGENT_PROFILE_FILE.unlink(missing_ok=True)
        human_setup.WELCOME_MESSAGE_FILE.unlink(missing_ok=True)

    if not _SETUP_DONE_FILE.exists():
        run_info = await setup()
        profile_file = human_setup.create_profile_file(
            with_recording=run_info["agent"]["terminal_recording"] != "NO_TERMINAL_RECORDING",
            env=get_task_env(),
        )
        human_setup.ensure_sourced(AGENT_HOME_DIR / ".profile", profile_file)
        _SETUP_DONE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SETUP_DONE_FILE.touch()

    if clock.get_status() == clock.ClockStatus.RUNNING:
        # Let any existing log calls finish
        await asyncio.sleep(0.5)
        await clock.pause(force=True)
    await asyncio.sleep(float("inf"))


@click.command()
@click.option("--reset", is_flag=True, help="Reset the agent setup", default=False)
def main(reset: bool):
    asyncio.run(_main(reset))


if __name__ == "__main__":
    main()
