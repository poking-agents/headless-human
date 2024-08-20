import itertools
import json

AI_TOOLS = ["NO_AI_TOOLS", "AI_TOOLS_AVAILABLE"]

TERMINAL_GIFS = ["TERMINAL_GIFS", "NO_TERMINAL_GIFS"]

MANIFEST = {
    "settingsSchema": {
        "type": "object",
        "properties": {
            "ai_tools": {
                "type": "string",
                "enum": AI_TOOLS + ["UNKNOWN_IF_AI_TOOLS_AVAILABLE"],
            },
            "terminal_gifs": {
                "type": "string",
                "enum": TERMINAL_GIFS,
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


def generate_manifest():

    axis = [AI_TOOLS, TERMINAL_GIFS]
    combinations = list(itertools.product(*axis))

    setting_packs = {}
    for ai_tool, terminal_gif in combinations:
        terminal_gif_name = "" if terminal_gif == "NO_TERMINAL_GIFS" else terminal_gif
        setting_pack_name = "-".join([ai_tool, terminal_gif_name])
        if setting_pack_name[-1] == "-":
            setting_pack_name = setting_pack_name[:-1]
        setting_packs[setting_pack_name] = {
            "ai_tools": ai_tool,
            "terminal_gifs": terminal_gif,
        }

    default_setting_pack = {
        "ai_tools": "UNKNOWN_IF_AI_TOOLS_AVAILABLE",
        "terminal_gifs": "NO_TERMINAL_GIFS",
    }
    setting_packs["UNKNOWN_IF_AI_TOOLS_AVAILABLE"] = (
        default_setting_pack
    )

    MANIFEST["settingsPacks"] = setting_packs
    MANIFEST["defaultSettingsPack"] = "UNKNOWN_IF_AI_TOOLS_AVAILABLE"
    with open("manifest.json", "w") as f:
        f.write(json.dumps(MANIFEST, indent=4, sort_keys=True))


if __name__ == "__main__":
    generate_manifest()
