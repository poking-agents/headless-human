import asyncio

import click
import src.clock as clock
from src.util import AGENT_HOME_DIR, HOOKS

_SUBMISSION_PATH = AGENT_HOME_DIR / "submission.txt"


async def _main(submission):
    if clock.get_status() == clock.ClockStatus.STOPPED:
        click.echo("Cannot submit: clock is stopped.")
        return

    confirmation = click.prompt(
        f"Do you definitely want to end the task and submit '{submission}'?",
        type=click.Choice(["y", "n"]),
        show_choices=True,
    ).lower()

    if confirmation == "n":
        click.echo("Submission cancelled.")
        return

    click.echo(f"SUBMITTED: {submission}")
    click.echo("CLOCK WILL BE STOPPED AUTOMATICALLY")
    click.echo("TASK IS OVER!")
    click.echo("From all of the METR team: thank you for your work!")

    _SUBMISSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SUBMISSION_PATH.write_text(submission)
    await HOOKS.submit(submission)


@click.command()
@click.argument("submission", type=str)
def main(submission: str):
    asyncio.run(_main(submission))


if __name__ == "__main__":
    main()
