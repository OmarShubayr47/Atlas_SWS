"""Schematics by voice: the assistant-facing layer over software/schematic/.

    "Draw an LED circuit for 5 volts"        -> create_schematic(led_resistor, {Vs: 5 V})
    "Change the LED current to 15 milliamps" -> modify_schematic("", {If: 15 mA})

The model chooses the template and passes the values it heard; everything
else is computed in schematic/templates.py. Results are saved in the
workspace as numbered revisions (never overwritten) and shown on the
projector. The text returned here is what the assistant says, so it carries
the computed values and every assumption, word for word.
"""
from datetime import datetime

from schematic import render, store, templates
from schematic.values import BadValue

from . import safety, view


def _folder():
    return safety.ensure_workspace() / "schematics"


def list_schematic_templates() -> str:
    lines = []
    for t in templates.TEMPLATES.values():
        params = []
        for p in t.params:
            extra = (f", default {p.default}" if p.default
                     else ", optional" if p.optional else "")
            params.append(f"{p.name} ({p.help}{extra})")
        lines.append(f"{t.name}: {t.title}. {t.description} Parameters: {'; '.join(params)}.")
    return "\n".join(lines)


def _build(template_name: str, inputs: dict, title: str):
    t = templates.get(template_name)
    vals, assumptions = templates.resolve(t, inputs)
    result = t.compute(vals, assumptions)
    title = (title or "").strip()[:80] or t.title
    svg = render.render(t, result, title)
    spec = {
        "template": t.name,
        "title": title,
        "inputs": {k: str(v) for k, v in inputs.items()},
        "values": result.values,
        "derived": result.derived,
        "assumptions": result.assumptions,
        "notes": result.notes,
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "generator": "sws schematic templates v1 (schemdraw)",
    }
    path, revision = store.save(_folder(), spec, svg)
    view.show(path)
    return result, title, path, revision


def _summary(verb: str, title: str, path, result) -> str:
    parts = [f"{verb} '{title}' as {safety.display(path)}"]
    if result.derived:
        parts.append("; ".join(f"{label} {text}" for label, text in result.derived))
    if result.assumptions:
        parts.append("Assumed: " + " ".join(result.assumptions))
    parts.append("It is on the projector")
    return ". ".join(parts) + "."


def create_schematic(template: str, values: dict | None = None, title: str = "") -> str:
    try:
        result, title, path, _ = _build(template, dict(values or {}), title)
    except BadValue as e:
        raise safety.ToolError(str(e))
    return _summary("Drew", title, path, result)


def modify_schematic(name: str = "", values: dict | None = None) -> str:
    found = store.latest(_folder(), name)
    if found is None:
        raise safety.ToolError(
            f"I couldn't find a schematic called '{name}'. Ask me to show the "
            "schematics folder to see their names." if name else
            "There is no schematic yet. Ask me to draw one first.")
    spec, _ = found
    inputs = dict(spec.get("inputs", {}))
    for key, value in (values or {}).items():
        match = next((k for k in inputs if k.lower() == str(key).lower()), str(key))
        inputs[match] = value
    try:
        result, title, path, revision = _build(spec["template"], inputs, spec["title"])
    except BadValue as e:
        raise safety.ToolError(str(e))
    return _summary(f"Updated (revision {revision})", title, path, result)
