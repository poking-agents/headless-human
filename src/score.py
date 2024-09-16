import argparse
import asyncio
import json

from src.settings import HOOKS, async_cleanup


async def score():
    result = await HOOKS.score()
    if result.status == "invalidSubmission":
        print("Your submission is invalid. Please try again.")
    elif result.status == "processFailed":
        print(f"Scoring failed. Please try again.")
    else:
        print(f"Score: {result.score}")

    if result.execResult is not None:
        print(f"Stdout:\n{result.execResult.stdout}")
        print(f"Stderr:\n{result.execResult.stderr}")

    if result.message is not None:
        print(json.dumps(result.message, indent=2))

    await async_cleanup()


async def log():
    score_log = await HOOKS.scoreLog()
    if not score_log:
        print("No score log found")
    else:
        for idx, entry in enumerate(score_log, start=1):
            print(f"{idx} - {entry.elapsedSeconds} sec - {entry.score}")
            for line in json.dumps(entry.message, indent=2).splitlines():
                print(f"  {line}")

    await async_cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ACTION", type=str, choices=["score", "log"])
    args = parser.parse_args()

    if args.ACTION == "score":
        asyncio.run(score())
    elif args.ACTION == "log":
        asyncio.run(log())
