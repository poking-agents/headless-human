import itertools
import json

_OPTIONS = {
    "ai_tools": ["NO_AI_TOOLS", "AI_TOOLS_AVAILABLE"],
    "terminal_recording": [
        "NO_TERMINAL_RECORDING",
        "TEXT_TERMINAL_RECORDING",
        "GIF_TERMINAL_RECORDING",
        "FULL_TERMINAL_RECORDING",
    ],
}


def generate_manifest():
    combinations = sorted(list(itertools.product(*_OPTIONS.values())))
    setting_packs = {}
    for combination in combinations:
        setting_pack_name = "-".join(combination)
        if setting_pack_name[-1] == "-":
            setting_pack_name = setting_pack_name[:-1]
        setting_packs[setting_pack_name] = dict(zip(_OPTIONS.keys(), combination))

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
                    "enum": _OPTIONS["ai_tools"] + ["UNKNOWN_IF_AI_TOOLS_AVAILABLE"],
                },
                "terminal_recording": {
                    "type": "string",
                    "enum": _OPTIONS["terminal_recording"],
                },
            },
            "additionalProperties": False,
            "required": list(_OPTIONS.keys()),
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
