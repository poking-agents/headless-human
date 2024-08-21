import asyncio
import inspect
import uvicorn
import json
import sys
import shutil
import os
import aiofiles
import subprocess
from pyhooks import Hooks
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from typing import Dict
from util import (
    HOOK_SERVER_PORT,
    HOOK_ACTIVITY_LOG_PATH,
    INITIAL_SETUP_PATH,
    USE_HOOK_LOG_PATH,
    local_mode,
    TERMINAL_LOG_PATH,
    SETUP_FLAG_PATH,
    READ_THIS_FIRST_INTERNAL_PATH,
    READ_THIS_FIRST_PATH,
    CLOCK_JSONL_PATH,
)


def get_methods(obj: object) -> Dict[str, bool]:
    """Return a dictionary whose keys are the names of the object's methods and whose values are booleans indicating whether the method is asynchronous"""
    methods = {}
    for name, method in inspect.getmembers(obj, predicate=inspect.ismethod):
        is_async = asyncio.iscoroutinefunction(method)
        methods[name] = is_async
    return methods


async def log(content: dict) -> None:
    """Log the content to the hooks_activity.jsonl file with a timestamp"""
    async with aiofiles.open(HOOK_ACTIVITY_LOG_PATH, "a") as f:
        timestamp = datetime.now().isoformat()
        print(f'{{"timestamp": "{timestamp}", "content":{content}}}')
        await f.write(f'{{"timestamp": "{timestamp}", "content":{content}}}\n')


app = FastAPI()


@app.get("/test")
async def test():
    return {"output": "success"}


if not local_mode:

    @app.post("/")
    async def forward(request: Request):
        data = await request.json()

        if data is None:
            await log({"error": "No data received"})
            raise HTTPException(status_code=400, detail="No data received")

        elif "hook" not in data or "content" not in data:
            await log(
                {
                    "error": "Invalid data format, must include 'hook' and 'content' keys",
                    "data": data,
                }
            )
            raise HTTPException(
                status_code=400,
                detail="Invalid data format, must include 'hook' and 'content' keys",
            )

        elif data["hook"] not in hook_methods:
            await log(
                {
                    "error": f"Hook '{data['hook']}' not found",
                    "data": {data},
                    "available_hooks": hook_methods,
                }
            )
            raise HTTPException(
                status_code=400, detail=f"Hook '{data['hook']}' not found"
            )

        elif "args" not in data["content"] or "kwargs" not in data["content"]:
            await log(
                {
                    "error": "Invalid content format, must include 'args' and 'kwargs' keys",
                    "data": data,
                }
            )
            raise HTTPException(
                status_code=400,
                detail="Invalid content format, must include 'args' and 'kwargs' keys",
            )

        else:
            try:
                if hook_async_map[data["hook"]]:
                    output = await getattr(hooks, data["hook"])(
                        *data["content"]["args"], **data["content"]["kwargs"]
                    )
                else:
                    output = getattr(hooks, data["hook"])(
                        *data["content"]["args"], **data["content"]["kwargs"]
                    )
                await log(
                    {"hook": data["hook"], "content": data["content"], "output": output}
                )
                # check if output is JSON serializable
                try:
                    json.dumps(output)
                    return {"output": output}
                except TypeError as e:
                    # If not, convert object to dict
                    return {"output": output.__dict__}
            except Exception as e:
                await log({"error": str(e), "data": data})
                raise HTTPException(status_code=400, detail=str(e))

elif local_mode:

    @app.post("/")
    async def local(request: Request):
        data = await request.json()
        if data.get("hook") is None:
            return {"output": "hook not provided", "input": data}
        if data["hook"] == "getTask":
            return {
                "output": {
                    "instructions": "some task instructions",
                    "permissions": "some task permissions",
                }
            }
        if data["hook"] == "pause":
            return {"output": "paused"}
        if data["hook"] == "log":
            return {"output": "logged"}
        if data["hook"] == "log_with_attributes":
            return {"output": "logged"}
        if data["hook"] == "getTask":
            return {"output": "family/task1"}
        if data["hook"] == "unpause":
            return {"output": "unpaused"}
        else:
            return {"output": "not implemented"}


async def start_server():
    config = uvicorn.Config(app, host="0.0.0.0", port=HOOK_SERVER_PORT, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()


async def main(*args):
    current_env = os.environ.copy()
    subprocess.Popen([sys.executable, INITIAL_SETUP_PATH], env=current_env)

    if local_mode:
        Path(SETUP_FLAG_PATH).unlink(missing_ok=True)
        Path(TERMINAL_LOG_PATH).unlink(missing_ok=True)
        Path(HOOK_ACTIVITY_LOG_PATH).unlink(missing_ok=True)
        Path(USE_HOOK_LOG_PATH).unlink(missing_ok=True)
        Path(CLOCK_JSONL_PATH).unlink(missing_ok=True)
        
        shutil.copyfile(READ_THIS_FIRST_INTERNAL_PATH, READ_THIS_FIRST_PATH)

        try:
            subprocess.run("lsof -t -i:8023 | xargs kill -9", shell=True, check=True)
            subprocess.run("lsof -t -i:8024 | xargs kill -9", shell=True, check=True)
        except subprocess.CalledProcessError:
            print("No processes were killed on ports 8023 and 8024")

        print("Starting local hook server")
        await start_server()
    else:
        await start_server()


if __name__ == "__main__":
    hooks = Hooks()
    hook_async_map = get_methods(hooks)
    hook_methods = list(hook_async_map.keys())

    if local_mode:
        asyncio.run(main())
    else:
        hooks.main(main)
