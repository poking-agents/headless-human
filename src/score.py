import argparse
import asyncio
import enum
import json
import tempfile

import aiofiles
import prettytable

import src.clock as clock
from src.settings import HOOKS, async_cleanup


class ScoreAction(enum.Enum):
    SCORE = "score"
    LOG = "log"


def get_header(header: str, width: int = 80):
    if header:
        header = f" {header} ".upper()
    header = header.ljust((width + len(header)) // 2, "=")
    header = header.rjust(width, "=")
    return header


def get_proc_output(stream: str, output: str):
    proc_output = [
        f"{stream}:".upper(),
        *(output.splitlines()),
        "",
    ]
    return proc_output


async def score():
    print("Running scoring, please wait...")

    result, _ = await asyncio.gather(
        HOOKS.score(),
        HOOKS.log("Scoring..."),
    )
    output = [get_header("SCORE RESULTS")]
    if result.status == "invalidSubmission":
        output.append("Your submission is invalid. Please try again.")
    elif result.status == "processFailed":
        output.append("Scoring failed. Please try again.")
    else:
        output.append(f"Score: {result.score}")

    if result.message is not None:
        output.append(get_header("DETAILS"))
        for k, v in result.message.items():
            output.append(f"{k}: {v}")

    if result.execResult is not None:
        output.append(get_header("EXECUTION RESULTS"))
        if result.execResult.stdout:
            output.extend(get_proc_output("stdout", result.execResult.stdout))
        if result.execResult.stderr:
            output.extend(get_proc_output("stderr", result.execResult.stderr))
    output.append(get_header(""))

    output_str = "\n".join(output)
    print(output_str)
    await HOOKS.log(output_str)

    return result.dict()


def seconds_to_time(seconds: int) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:0>2.0f}:{minutes:0>2.0f}:{seconds:0>2.0f}"


async def log():
    print("Requesting score log, please wait...")

    score_log, _ = await asyncio.gather(
        HOOKS.scoreLog(),
        HOOKS.log("Requested score log"),
    )
    if not score_log:
        output = "No score log found"
        print(output)
        await HOOKS.log(output)
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

    table_str = table.get_string()
    print(table_str)
    await HOOKS.log(table_str)

    return [entry.dict() for entry in score_log]


async def main(action: str | ScoreAction):
    if clock.get_status() != clock.ClockStatus.RUNNING:
        clock_status = await clock.clock()
        if clock_status != clock.ClockStatus.RUNNING:
            return

    action = ScoreAction(action)
    if action == ScoreAction.SCORE:
        result = await score()
    elif action == ScoreAction.LOG:
        result = await log()

    _, output_file = tempfile.mkstemp(suffix=".json")
    async with aiofiles.open(output_file, "w") as f:
        await f.write(json.dumps(result))

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
