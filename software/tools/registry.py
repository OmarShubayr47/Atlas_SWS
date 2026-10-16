"""Tool definitions and dispatch, independent of which API calls them.

Chat completions and the Realtime API want the same information in slightly
different envelopes:

    chat completions   {"type": "function", "function": {name, description,
                                                         parameters}}
    realtime           {"type": "function", name, description, parameters}

So the canonical definition is stored once and the envelope is generated per
transport. That is the whole reason this module exists separately from
files.py: voice_assistant.py works today and voice_realtime.py does not, and
neither should own the tool definitions.

Adding a tool means adding one Tool() entry here. Nothing else changes.
"""
import json
from dataclasses import dataclass
from typing import Any, Callable

from schematic import templates as schematic_templates

from . import files, safety, schematics, view, workspace


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict
    fn: Callable[..., str]


def _schema(properties: dict, required: list[str]) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


TOOLS: dict[str, Tool] = {
    t.name: t for t in [
        Tool(
            name="find_file",
            description=(
                "Find files in the Smart Working Station project by name. "
                "Use when the user asks where something is, or refers to a "
                "file without giving its full path."
            ),
            parameters=_schema(
                {"name_fragment": {
                    "type": "string",
                    "description": "Part of the filename, e.g. 'mic' or 'decisions'.",
                }},
                ["name_fragment"],
            ),
            fn=files.find_file,
        ),
        Tool(
            name="list_directory",
            description=(
                "List the contents of a directory in the project. Use to "
                "explore structure when the user asks what is in a folder."
            ),
            parameters=_schema(
                {"path": {
                    "type": "string",
                    "description": (
                        "Directory relative to the project root, e.g. "
                        "'software/common'. Use '.' for the project root."
                    ),
                }},
                ["path"],
            ),
            fn=files.list_directory,
        ),
        Tool(
            name="read_file",
            description=(
                "Read a text file from the project. Use when the user asks "
                "what a file does or what it contains. Prefer search_code "
                "for large files."
            ),
            parameters=_schema(
                {"path": {
                    "type": "string",
                    "description": "File path relative to the project root.",
                }},
                ["path"],
            ),
            fn=files.read_file,
        ),
        Tool(
            name="search_code",
            description=(
                "Search all project text files for a string. Use to find "
                "where something is defined or used, e.g. a GPIO number, a "
                "function name, or a hardware part number."
            ),
            parameters=_schema(
                {"query": {
                    "type": "string",
                    "description": "Text to search for, e.g. 'GPIO 22' or 'MAX98357A'.",
                }},
                ["query"],
            ),
            fn=files.search_code,
        ),
        Tool(
            name="project_status",
            description=(
                "Report the project's current git branch, last commit, and "
                "how many files have uncommitted changes."
            ),
            parameters=_schema({}, []),
            fn=files.project_status,
        ),
        # --- the projector viewer (tools/view.py) -------------------------
        Tool(
            name="open_file",
            description=(
                "Show a file on the projector: text or code, images (png, "
                "jpg, svg) or PDFs; a folder shows its contents. Use for "
                "'open', 'show me', 'display'. Take the path from find_file, "
                "list_directory or show_workspace; the user's own files "
                "start with 'workspace/'."
            ),
            parameters=_schema(
                {"path": {
                    "type": "string",
                    "description": "Project-relative path, or 'workspace/...'.",
                }},
                ["path"],
            ),
            fn=view.open_file,
        ),
        Tool(
            name="control_view",
            description=(
                "Zoom, scroll or turn pages of whatever is shown on the "
                "projector. Call once per step the user asks for."
            ),
            parameters=_schema(
                {"action": {
                    "type": "string",
                    "enum": list(view.CONTROL_ACTIONS),
                    "description": "What to do with the current view.",
                }},
                ["action"],
            ),
            fn=view.control_view,
        ),
        Tool(
            name="close_view",
            description=(
                "Close the file shown on the projector and return to the "
                "assistant screen."
            ),
            parameters=_schema({}, []),
            fn=view.close_view,
        ),
        # --- the user's workspace (tools/workspace.py) -------------------
        Tool(
            name="show_workspace",
            description=(
                "List the user's own files (notes, documents, schematics) on "
                "the projector, newest first and numbered, so they can say "
                "'open number two'."
            ),
            parameters=_schema(
                {"folder": {
                    "type": "string",
                    "enum": ["", *safety.WORKSPACE_DIRS],
                    "description": "One folder, or '' for everything.",
                }},
                [],
            ),
            fn=workspace.show_workspace,
        ),
        Tool(
            name="create_note",
            description=(
                "Save a new note in the user's workspace and show it. For "
                "'make a note', 'write this down', 'note that'. Creates a new "
                "file every time; it never changes or replaces an old one."
            ),
            parameters=_schema(
                {
                    "title": {"type": "string",
                              "description": "Short title; also the file name."},
                    "text": {"type": "string",
                             "description": "The note itself, in Markdown."},
                },
                ["title", "text"],
            ),
            fn=workspace.create_note,
        ),
        Tool(
            name="create_text_file",
            description=(
                "Create a new text file (.txt, .md, .csv, .py or .json) in the "
                "workspace documents folder and show it, e.g. a parts list as "
                "CSV or a short script. Files are saved, never run. Never "
                "replaces an existing file."
            ),
            parameters=_schema(
                {
                    "filename": {"type": "string",
                                 "description": "File name with extension, e.g. 'parts.csv'."},
                    "content": {"type": "string",
                                "description": "The complete file content."},
                },
                ["filename", "content"],
            ),
            fn=workspace.create_text_file,
        ),
        # --- schematics by voice (tools/schematics.py) --------------------
        Tool(
            name="create_schematic",
            description=(
                "Draw a circuit schematic from a template, save it in the "
                "workspace and show it on the projector. Templates and their "
                "parameters (? = optional or has a default): "
                + schematic_templates.summary()
                + ". Pass only the values the user said, with units, e.g. "
                "{\"Vin\": \"5 V\", \"R1\": \"10k\"}. Everything else is "
                "computed; never make up component values. If no template "
                "fits, say so instead of forcing one."
            ),
            parameters=_schema(
                {
                    "template": {"type": "string",
                                 "enum": list(schematic_templates.TEMPLATES)},
                    "values": {"type": "object",
                               "additionalProperties": {"type": "string"},
                               "description": "Parameter name -> value as said, with units."},
                    "title": {"type": "string",
                              "description": "Optional short title, e.g. 'LED for 5 V'."},
                },
                ["template", "values"],
            ),
            fn=schematics.create_schematic,
        ),
        Tool(
            name="modify_schematic",
            description=(
                "Change values in an existing schematic and redraw it as a new "
                "revision (older revisions are kept). Use for 'change R2 to "
                "10k', 'make the current 15 milliamps'. name '' means the most "
                "recent schematic."
            ),
            parameters=_schema(
                {
                    "name": {"type": "string",
                             "description": "Schematic title or folder name, or ''."},
                    "values": {"type": "object",
                               "additionalProperties": {"type": "string"},
                               "description": "Parameters to change; '' removes one."},
                },
                ["values"],
            ),
            fn=schematics.modify_schematic,
        ),
        Tool(
            name="list_schematic_templates",
            description="Describe every circuit template and its parameters in detail.",
            parameters=_schema({}, []),
            fn=schematics.list_schematic_templates,
        ),
    ]
}


def chat_schemas() -> list[dict]:
    """Tool list for the chat completions `tools` parameter."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in TOOLS.values()
    ]


def realtime_schemas() -> list[dict]:
    """Tool list for the Realtime API's session.tools."""
    return [
        {
            "type": "function",
            "name": t.name,
            "description": t.description,
            "parameters": t.parameters,
        }
        for t in TOOLS.values()
    ]


def dispatch(name: str, arguments: str | dict[str, Any]) -> str:
    """Run a tool call and return its result as a string.

    Never raises. A tool that fails returns its error message as the result,
    because the model needs to hear *why* in order to correct itself — an
    exception propagating up would just end the conversation turn instead.
    """
    tool = TOOLS.get(name)
    if tool is None:
        return f"Unknown tool '{name}'. Available: {', '.join(TOOLS)}"

    if isinstance(arguments, str):
        try:
            args = json.loads(arguments) if arguments.strip() else {}
        except json.JSONDecodeError as e:
            return f"Could not parse arguments for {name}: {e}"
    else:
        args = arguments or {}

    # Drop anything not in the schema rather than passing it through to a
    # TypeError. Models occasionally invent plausible-sounding extra keys.
    allowed = set(tool.parameters.get("properties", {}))
    filtered = {k: v for k, v in args.items() if k in allowed}

    try:
        return tool.fn(**filtered)
    except safety.ToolError as e:
        return str(e)
    except TypeError as e:
        return f"Wrong arguments for {name}: {e}"
    except Exception as e:  # noqa: BLE001 - must not kill the voice loop
        return f"{name} failed: {type(e).__name__}: {e}"
