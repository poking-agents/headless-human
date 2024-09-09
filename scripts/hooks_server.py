from __future__ import annotations

import argparse
import asyncio
import datetime
import inspect
import json
import pathlib
from typing import Any

import aiofiles
import fastapi
import pyhooks
import uvicorn

app = fastapi.FastAPI()

HOOK_ACTIVITY_LOG_PATH = pathlib.Path.cwd() / "hooks_activity.jsonl"


async def log(content: dict) -> None:
    """Log the content to the hooks_activity.jsonl file with a timestamp"""
    HOOK_ACTIVITY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat()
    entry = json.dumps({"timestamp": timestamp, "content": content})
    print(entry)
    async with aiofiles.open(HOOK_ACTIVITY_LOG_PATH, "a") as f:
        await f.write(f"{entry}\n")


def get_methods(cls: type) -> dict[str, bool]:
    """Return a dictionary whose keys are the names of the object's methods and
    whose values are booleans indicating whether the method is asynchronous"""

    methods = {}
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if isinstance(inspect.getattr_static(cls, name), staticmethod):
            continue

        is_async = asyncio.iscoroutinefunction(method)
        methods[name] = is_async
    return methods


HOOKS_ASYNC_MAP = get_methods(pyhooks.Hooks)


@app.get("/test")
async def test():
    return {"output": "success"}


@app.post("/")
async def local(request: fastapi.Request):
    data: dict[str, Any] | None = await request.json()
    if not data or (hook := data.pop("hook")) is None:
        raise fastapi.HTTPException(status_code=400, detail="hook not provided")

    if hook not in HOOKS_ASYNC_MAP:
        raise fastapi.HTTPException(status_code=400, detail="hook not implemented")

    await log(data)
    return {"hook": hook, "output": "success"}


async def main(port: int, clear_log: bool = False):
    if clear_log:
        HOOK_ACTIVITY_LOG_PATH.unlink(missing_ok=True)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8023)
    parser.add_argument("--clear", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.port, args.clear))
