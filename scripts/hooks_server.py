from __future__ import annotations

import asyncio
import datetime
import json
import pathlib

import aiofiles
import click
import fastapi
import pyhooks
import uvicorn

app = fastapi.FastAPI()

ACTIVITY_LOG_FILE = pathlib.Path.cwd() / "hooks_activity.jsonl"


@app.get("/test")
async def test():
    return {"output": "success"}


@app.get("/getTaskInstructions")
async def get_task_instructions():
    settings_file = pathlib.Path("/home/agent/.agent_code/settings.json")
    settings = (
        json.loads(settings_file.read_text())["task"]
        if settings_file.exists()
        else pyhooks.TaskInfo(
            instructions="No instructions found",
            permissions=[],
        ).dict()
    )

    try:
        return {"result": {"data": settings}}
    except Exception as e:
        raise fastapi.HTTPException(status_code=500, detail=str(e))


@app.post("/{hook:path}")
async def local(request: fastapi.Request, hook: str):
    try:
        data = await request.json()
    except fastapi.HTTPException:
        data = None

    try:
        timestamp = datetime.datetime.now().isoformat()
        entry = json.dumps({"timestamp": timestamp, "hook": hook, "data": data})
        click.echo(entry)
        ACTIVITY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(ACTIVITY_LOG_FILE, "a") as f:
            await f.write(f"{entry}\n")

        return {"result": {"success": True}}
    except Exception as e:
        raise fastapi.HTTPException(status_code=500, detail=str(e))


async def _main(port: int, clear_log: bool = False):
    if clear_log:
        ACTIVITY_LOG_FILE.unlink(missing_ok=True)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, loop="asyncio")
    server = uvicorn.Server(config)
    click.echo("Starting hooks server")
    click.echo("Add the following to your shell profile")
    for key, value in (
        ("API_IP", f"http://localhost:{port}"),
        ("RUN_ID", "0"),
        ("AGENT_TOKEN", "local"),
        ("TASK_ID", "foo/gar"),
    ):
        click.echo(f"  export {key}={value}")

    await server.serve()


@click.command()
@click.option("--port", type=int, default=8023)
@click.option("--clear", is_flag=True)
def main(port: int, clear: bool):
    asyncio.run(_main(port, clear))


if __name__ == "__main__":
    main()
