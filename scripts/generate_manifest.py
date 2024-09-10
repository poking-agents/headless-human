import itertools
import json

AI_TOOLS = ["NO_AI_TOOLS", "AI_TOOLS_AVAILABLE"]

TERMINAL_RECORDING = [
    "NO_TERMINAL_RECORDING",
    "TEXT_TERMINAL_RECORDING",
    "GIF_TERMINAL_RECORDING",
    "FULL_TERMINAL_RECORDING",
]


def generate_manifest():
    axis = {
        "ai_tools": AI_TOOLS,
        "terminal_recording": TERMINAL_RECORDING,
    }
    combinations = sorted(list(itertools.product(*axis.values())))

    setting_packs = {}
    for combination in combinations:
        setting_pack_name = "-".join(combination)
        if setting_pack_name[-1] == "-":
            setting_pack_name = setting_pack_name[:-1]
        setting_packs[setting_pack_name] = dict(zip(axis.keys(), combination))

    default_setting_pack = "UNKNOWN_IF_AI_TOOLS_AVAILABLE"
    setting_packs[default_setting_pack] = {
        "ai_tools": "UNKNOWN_IF_AI_TOOLS_AVAILABLE",
        "terminal_recording": "NO_TERMINAL_RECORDING",
    }

    manifest = {
        "settingsPacks": setting_packs,
        "defaultSettingsPack": default_setting_pack,
        "settingsSchema": {
            "type": "object",
            "properties": {
                "ai_tools": {
                    "type": "string",
                    "enum": AI_TOOLS + ["UNKNOWN_IF_AI_TOOLS_AVAILABLE"],
                },
                "terminal_recording": {
                    "type": "string",
                    "enum": TERMINAL_RECORDING,
                },
            },
            "additionalProperties": False,
            "required": ["ai_tools", "terminal_gifs"],
        },
        "stateSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
            "required": [""],
        },
    }
    with open("manifest.json", "w") as f:
        f.write(json.dumps(manifest, indent=4, sort_keys=True))


if __name__ == "__main__":
    generate_manifest()
