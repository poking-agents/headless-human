import asyncio
import time

import click
from src.clock import LOG_ATTRIBUTES, ClockStatus, record_status
from src.util import HOOKS, INTERNAL_SUBMISSION_PATH, get_timestamp


async def _main(submission):
    confirmation = click.prompt(
        f"Do you definitely want to end the task and submit '{submission}'?",
        type=click.Choice(["y", "n"]),
        show_choices=True,
    ).lower()

    if confirmation == "n":
        print("Submission cancelled.")
        return

    if confirmation == "y":
        await HOOKS.pause()
        HOOKS.log_with_attributes(
            LOG_ATTRIBUTES,
            f"⏰ Clock stopped at {get_timestamp()}",
        )

        record_status(ClockStatus.STOPPED)

        print(f"SUBMITTED: {submission}")
        print("CLOCK WILL BE STOPPED AUTOMATICALLY")
        print("TASK IS OVER!")
        print("From all of the METR team: thank you for your work!")

        # Using an internal path to avoid unintended submissions if humans write
        # to `/home/agent/submission.txt` directly
        with open(
            INTERNAL_SUBMISSION_PATH, "w"
        ) as file:  # Writing this file to alert other processes to wrap up
            file.write(submission)

        time.sleep(5)  # Time to allow other processes to wrap up

        await HOOKS.submit(submission)


@click.command()
@click.argument("submission", type=str)
def main(submission: str):
    asyncio.run(_main(submission))


if __name__ == "__main__":
    main()
