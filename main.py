import asyncio
import inspect
import time
import requests
import threading
import subprocess
from pyhooks import Hooks
from datetime import datetime
from flask import Flask, request, jsonify
from asgiref.sync import async_to_sync
from typing import Dict
from util import HOOK_SERVER_PORT, HOOK_ACTIVITY_LOG_PATH, INITIAL_SETUP_PATH


def get_methods(obj: object) -> Dict[str, bool]:
    """Return a dictionary whose keys are the names of the object's methods and whose values are booleans indicating whether the method is asynchronous"""
    methods = {}
    for name, method in inspect.getmembers(obj, predicate=inspect.ismethod):
        is_async = asyncio.iscoroutinefunction(method)
        methods[name] = is_async
    return methods


def log(content: dict) -> None:
    """Log the content to the hooks_activity.jsonl file with a timestamp"""
    with open(HOOK_ACTIVITY_LOG_PATH, "a") as f:
        timestamp = datetime.now().isoformat()
        print(f'{{"timestamp": "{timestamp}", "content":{content}}}')
        f.write(f'{{"timestamp": "{timestamp}", "content":{content}}}\n')


def run_flask_app(app, port):
    app.run(port=port)


app = Flask(__name__)


@app.route("/", methods=["POST"])
def forward():
    data = request.get_json()

    if data is None:
        log({"error": "No data received"})
        return jsonify({"error": "No data received"}), 400

    elif "hook" not in data or "content" not in data:
        log(
            {
                "error": "Invalid data format, must include 'hook' and 'content' keys",
                "data": data,
            }
        )
        return (
            jsonify(
                {"error": "Invalid data format, must include 'hook' and 'content' keys"}
            ),
            400,
        )

    elif data["hook"] not in hook_methods:
        log(
            {
                "error": f"Hook '{data['hook']}' not found",
                "data": {data},
                "available_hooks": hook_methods,
            }
        )
        return jsonify({"error": f"Hook '{data['hook']}' not found"}), 400

    elif "args" not in data["content"] or "kwargs" not in data["content"]:
        log(
            {
                "error": "Invalid content format, must include 'args' and 'kwargs' keys",
                "data": data,
            }
        )
        return (
            jsonify(
                {
                    "error": "Invalid content format, must include 'args' and 'kwargs' keys"
                }
            ),
            400,
        )

    else:
        try:
            if hook_async_map[data["hook"]]:
                sync_hook = async_to_sync(getattr(hooks, data["hook"]))
                output = sync_hook(
                    *data["content"]["args"], **data["content"]["kwargs"]
                )

            else:
                output = getattr(hooks, data["hook"])(
                    *data["content"]["args"], **data["content"]["kwargs"]
                )
            log({"hook": data["hook"], "content": data["content"], "output": output})
            return jsonify({"output": output}), 200
        except Exception as e:
            log({"error": str(e), "data": data})
            return jsonify({"error": str(e)}), 400


async def main(*args):
    flask_thread = threading.Thread(target=run_flask_app, args=(app, HOOK_SERVER_PORT))
    flask_thread.start()

    max_attempts = 10
    for _ in range(max_attempts):
        try:
            response = requests.post(f"http://localhost:{HOOK_SERVER_PORT}", json={})
            if response.status_code == 400:
                break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    else:
        raise Exception("Failed to connect to the hook server")

    subprocess.check_call(["python", INITIAL_SETUP_PATH])

    while True:
        time.sleep(1)


if __name__ == "__main__":
    hooks = Hooks()
    hook_async_map = get_methods(hooks)
    hook_methods = list(hook_async_map.keys())
    hooks.main(main)
