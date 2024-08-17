import inspect
import logging
import requests
from flask import Flask, jsonify
from util import get_timestamp, use_hook, TOOL_SERVER_PORT, TOOL_ACTIVITY_LOG_PATH

app = Flask(__name__)

app.logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(TOOL_ACTIVITY_LOG_PATH)
file_handler.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)
app.logger.addHandler(console_handler)

tool_log_styles = {
    "/clock/start": {
        "style": {"background-color": "#f7b7c5", "border-color": "#d17b80"}
    },
    "/clock/stop": {
        "style": {"background-color": "#f7b7c5", "border-color": "#d17b80"}
    },
    "/terminal/log": {
        "style": {
            "color": "white",
            "background-color": "#424345",
        }
    },
    "/note": {
        "style": {
            "color": "#2b2928",
            "padding": "5px",
            "border-radius": "5px",
            "border-width": "thick",
            "background-color": "#f7e2c8",
            "border-color": "#d9b38e",
            "font-style": "italic",
        }
    },
}


@app.route("/clock/start", methods=["POST"])
def start_clock():
    route_name = inspect.currentframe().f_code.co_name
    use_hook("unpause")
    use_hook(
        "log_with_attributes",
        args=[
            tool_log_styles[route_name],
            f"⏰ Clock started at {get_timestamp()}",
        ],
    )


@app.route("/clock/stop", methods=["POST"])
def stop_clock():
    route_name = inspect.currentframe().f_code.co_name
    use_hook("pause")
    use_hook(
        "log_with_attributes",
        args=[
            tool_log_styles[route_name],
            f"⏰ Clock stopped at {get_timestamp()}",
        ],
    )


@app.route("/terminal/gif", methods=["POST"])
def terminal_gif():
    use_hook("log_image", args=requests.get_json()["args"])


@app.route("/terminal/log", methods=["POST"])
def terminal_log():
    route_name = inspect.currentframe().f_code.co_name
    use_hook(
        "log_with_attributes",
        args=[tool_log_styles[route_name], requests.get_json()["args"]],
    )


@app.route("/note", methods=["POST"])
def note():
    route_name = inspect.currentframe().f_code.co_name
    use_hook(
        "log_with_attributes",
        args=[tool_log_styles[route_name], requests.get_json()["args"]],
    )


@app.route("/submit", methods=["POST"])
def submit():
    data = requests.get_json()
    use_hook("submit", args=data["args"])


if __name__ == "__main__":
    app.run(port=TOOL_SERVER_PORT)
