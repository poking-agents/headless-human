import itertools
import json

PEOPLE = [
    "ADAM_HANSON",
    "AMRITANSHU_PARAD",
    "AMY_NGO",
    "BEN_WEST",
    "BETH_BARNES",
    "BRIAN_GOODRICH",
    "CHRIS_BARNETT",
    "CHRIS_MACLEOD",
    "HAMISH_HUGGARD",
    "DAVIS_ELLIS",
    "JAI_DHYANI",
    "JEFFREY_HAINES",
    "JOEL_BECKER",
    "JOSH_CLYMER",
    "KATHERINE_WORDEN",
    "KATHY_GARCIA",
    "LAWRENCE_CHAN",
    "LUCAS_SATO",
    "MATT_GOLDWATER",
    "MATTHEW_WEARDEN",
    "MEGAN_KINNIMENT",
    "MIGUEL_BRANDAO",
    "MIHNEA_MAFTEI",
    "MARTIN_MILBRADT",
    "NIKOLA_JURKOVIC",
    "NOA_WEISS",
    "PIP_ARNOTT",
    "RAE_SHE",
    "RYAN_BLOOM",
    "SAMI_JAWHAR",
    "SUDARSH_KUNNAVAKKAM",
    "THOMAS_BROADLEY",
    "TIMOTHEE_CHAUVIN",
    "TIMOTHY_KOKOTAJILO",
]

AI_TOOLS = ["NO_AI_TOOLS", "AI_TOOLS_AVAILABLE"]

TERMINAL_GIFS = ["NO_TERMINAL_GIFS", "TERMINAL_GIFS"]

MANIFEST = {
    "settingsSchema": {
        "type": "object",
        "properties": {
            "person": {"type": "string", "enum": PEOPLE + ["UNKNOWN_PERSON"]},
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
        "required": ["person", "ai_tools", "terminal_gifs"],
    },
    "stateSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
        "required": [""],
    },
}


def generate_manifest():

    axis = [PEOPLE, AI_TOOLS, TERMINAL_GIFS]
    combinations = list(itertools.product(*axis))

    setting_packs = {}
    for person, ai_tool, terminal_gif in combinations:
        setting_pack_name = "-".join([person, ai_tool, terminal_gif])
        setting_packs[setting_pack_name] = {
            "person": person,
            "ai_tools": ai_tool,
            "terminal_gifs": terminal_gif,
        }

    default_setting_pack = {
        "person": "UNKNOWN_PERSON",
        "ai_tools": "UNKNOWN_IF_AI_TOOLS_AVAILABLE",
        "terminal_gifs": "TERMINAL_GIFS",
    }
    setting_packs["UNKNOWN_PERSON-UNKNOWN_IF_AI_TOOLS_AVAILABLE-TERMINAL_GIFS"] = (
        default_setting_pack
    )

    setting_packs["UNKNOWN_PERSON-UNKNOWN_IF_AI_TOOLS_AVAILABLE-NO_TERMINAL_GIFS"] = {
        "person": "UNKNOWN_PERSON",
        "ai_tools": "UNKNOWN_IF_AI_TOOLS_AVAILABLE",
        "terminal_gifs": "NO_TERMINAL_GIFS",
    }

    MANIFEST["settingsPacks"] = setting_packs
    MANIFEST["defaultSettingsPack"] = (
        "UNKNOWN_PERSON-UNKNOWN_IF_AI_TOOLS_AVAILABLE-TERMINAL_GIFS"
    )
    with open("manifest.json", "w") as f:
        f.write(json.dumps(MANIFEST, indent=4, sort_keys=True))


if __name__ == "__main__":
    generate_manifest()
