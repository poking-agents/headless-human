import argparse
import asyncio
import enum
import json
import tempfile

from src.settings import HOOKS, async_cleanup


class ScoreAction(enum.Enum):
    SCORE = "score"
    LOG = "log"


async def score():
    result = await HOOKS.score()
    if result.status == "invalidSubmission":
        print("Your submission is invalid. Please try again.")
    elif result.status == "processFailed":
        print("Scoring failed. Please try again.")
    else:
        print(f"Score: {result.score}")

    if result.execResult is not None:
        print(f"Stdout:\n{result.execResult.stdout}")
        print(f"Stderr:\n{result.execResult.stderr}")

    if result.message is not None:
        print(json.dumps(result.message, indent=2))

    return result.dict()


async def log():
    score_log = await HOOKS.scoreLog()
    if not score_log:
        print("No score log found")
        return []

    for idx, entry in enumerate(score_log, start=1):
        print(f"{idx} - {entry.elapsedSeconds} sec - {entry.score}")
        for line in json.dumps(entry.message, indent=2).splitlines():
            print(f"  {line}")

    return [entry.dict() for entry in score_log]


async def main(action: str | ScoreAction):
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
        choices=[action.value for action in ScoreAction],
    )
    args = parser.parse_args()

    asyncio.run(main(args.ACTION))
