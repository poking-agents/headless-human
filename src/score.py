import argparse
import asyncio
import enum
import json
import tempfile

import prettytable

from src.settings import HOOKS, async_cleanup
import src.clock as clock


class ScoreAction(enum.Enum):
    SCORE = "score"
    LOG = "log"


def print_header(header: str, width: int = 80):
    if header:
        header = f" {header} ".upper()
    header = header.ljust((width + len(header)) // 2, "=")
    header = header.rjust(width, "=")
    print(header)


def print_proc_output(stream: str, output: str):
    print(f"{stream}:".upper())
    print(output)
    print()


async def score():
    result = await HOOKS.score()
    print_header("SCORE RESULTS")
    if result.status == "invalidSubmission":
        print("Your submission is invalid. Please try again.")
    elif result.status == "processFailed":
        print("Scoring failed. Please try again.")
    else:
        print(f"Score: {result.score}")

    if result.message is not None:
        print_header("DETAILS")
        for k, v in result.message.items():
            print(f"{k}: {v}")

    if result.execResult is not None:
        print_header("EXECUTION RESULTS")
        if result.execResult.stdout:
            print_proc_output("stdout", result.execResult.stdout)
        if result.execResult.stderr:
            print_proc_output("stderr", result.execResult.stderr)
    print_header("")

    return result.dict()


def seconds_to_time(seconds: int) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:0>2.0f}:{minutes:0>2.0f}:{seconds:0>2.0f}"


async def log():
    score_log = await HOOKS.scoreLog()
    if not score_log:
        print("No score log found")
        return []

    table = prettytable.PrettyTable()
    table.field_names = ["Attempt", "Time", "Score", "Message"]
    for idx, entry in enumerate(score_log, start=1):
        first_message, *messages = list((entry.message or {}).items())
        table.add_row(
            [
                idx,
                seconds_to_time(entry.elapsedSeconds),
                entry.score,
                f"{first_message[0].title()}: {first_message[1]}",
            ]
        )
        for key, value in messages:
            table.add_row(["", "", "", f"{key.title()}: {value}"])
        table.add_row(["", "", "", ""])
    table.align["Message"] = "l"
    print(table)

    return [entry.dict() for entry in score_log]


async def main(action: str | ScoreAction):
    if clock.get_status() != clock.ClockStatus.RUNNING:
        await clock.main()
        if clock.get_status() != clock.ClockStatus.RUNNING:
            return

    action = ScoreAction(action)
    if action == ScoreAction.SCORE:
        result = await score()
    elif action == ScoreAction.LOG:
        result = await log()

    _, output_file = tempfile.mkstemp(suffix=".json")
    with open(output_file, "w") as f:
        json.dump(result, f)

    print(f"Raw output saved to {output_file}")

    await async_cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "ACTION",
        type=ScoreAction,
        choices=list(ScoreAction),
    )
    args = parser.parse_args()

    asyncio.run(main(args.ACTION))
