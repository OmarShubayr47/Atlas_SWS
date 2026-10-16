"""Show files on the projector, and steer what is being shown.

These tools only PUBLISH events (common/ui_events, fire-and-forget). The UI
server serves the file to the kiosk after checking the path again with
safety.safe_path, and the browser does the drawing, zooming and scrolling.
So a slow or absent display can never stall the assistant, and the same
viewer state can later be driven by touch gestures on the foil.

What can be shown: text and code (rendered as text — never executed or
interpreted as HTML), images including SVG (loaded through <img>, where an
SVG cannot run scripts), and PDFs (each page rendered to an image by
pdftoppm on the server).
"""
import pathlib
import subprocess
import threading
import time

from common import ui_events

from . import safety

TEXT_EXTS = {
    ".md", ".txt", ".py", ".json", ".csv", ".log", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".conf", ".sh", ".js", ".css", ".html", ".xml", ".c",
    ".h", ".cpp", ".service", ".scad",
}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
PDF_EXTS = {".pdf"}
MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_LIST_ITEMS = 40          # the UI server caps an event at 16 KB

CONTROL_ACTIONS = ("zoom_in", "zoom_out", "reset_zoom", "scroll_up",
                   "scroll_down", "next_page", "previous_page")

_lock = threading.Lock()
_on_screen: str | None = None    # display path (or list title) now shown


def kind_for(path: pathlib.Path) -> str | None:
    ext = path.suffix.lower()
    if ext in PDF_EXTS:
        return "pdf"
    if ext in IMAGE_EXTS:
        return "image"
    if ext in TEXT_EXTS:
        return "text"
    return None


def pdf_pages(path: pathlib.Path) -> int | None:
    """Page count from pdfinfo (poppler-utils), or None if it can't tell."""
    try:
        r = subprocess.run(["pdfinfo", str(path)], capture_output=True,
                           text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    for line in r.stdout.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split(":", 1)[1])
            except ValueError:
                return None
    return None


def friendly_name(path: pathlib.Path) -> str:
    """What to call a file on screen: schematic revisions by their title.

    workspace/schematics/LED_for_5_V/r2.svg -> "LED for 5 V — revision 2"
    """
    shown = safety.display(path)
    parts = shown.split("/")
    if (len(parts) == 4 and parts[:2] == [safety.WORKSPACE_PREFIX, "schematics"]
            and path.suffix.lower() == ".svg" and path.stem[1:].isdigit()):
        return f"{parts[2].replace('_', ' ')} — revision {path.stem[1:]}"
    return path.name


def _publish_open(**fields) -> None:
    global _on_screen
    with _lock:
        _on_screen = fields.get("path") or fields.get("title")
    ui_events.publish("view", action="open", **fields)


def show(path: pathlib.Path) -> str:
    """Put an already-validated file on the projector. Returns a short note."""
    kind = kind_for(path)
    if kind is None:
        raise safety.ToolError(
            f"I can't display {path.suffix or 'that kind of'} files on the projector yet."
        )
    shown = safety.display(path)
    fields = {"kind": kind, "path": shown, "title": friendly_name(path)}
    note = ""
    if kind == "text" and path.stat().st_size > MAX_TEXT_BYTES:
        raise safety.ToolError(f"{shown} is too large to show as text.")
    if kind == "pdf":
        pages = pdf_pages(path)
        fields["pages"] = pages or 1
        if pages:
            note = f" It has {pages} page{'s' if pages != 1 else ''}."
    # Schematics are drawn black on white; shown inverted on the projector,
    # where black is "no light".
    if kind == "image" and shown.startswith(f"{safety.WORKSPACE_PREFIX}/schematics/"):
        fields["invert"] = True
    _publish_open(**fields)
    return f"Showing {shown} on the projector.{note}"


def show_list(title: str, entries: list[pathlib.Path]) -> None:
    """Show a numbered list of files (newest first is the caller's job)."""
    items = []
    for i, p in enumerate(entries[:MAX_LIST_ITEMS], start=1):
        try:
            when = time.strftime("%d %b %H:%M", time.localtime(p.stat().st_mtime))
        except OSError:
            when = ""
        items.append({"n": i, "path": safety.display(p), "name": friendly_name(p),
                      "when": when})
    _publish_open(kind="list", title=title, items=items)


# --- tools --------------------------------------------------------------------

def open_file(path: str) -> str:
    """Show a project or workspace file (or a folder's contents)."""
    target = safety.safe_path(path)
    if target.is_dir():
        entries = sorted((p for p in target.iterdir()
                          if not safety.is_denied_name(p.name)),
                         key=lambda p: (p.is_dir(), p.name.lower()))
        show_list(safety.display(target), entries)
        names = ", ".join(p.name for p in entries[:12]) or "nothing"
        return f"Showing the folder {safety.display(target)}: {names}."
    return show(target)


def close_view() -> str:
    global _on_screen
    with _lock:
        was, _on_screen = _on_screen, None
    ui_events.publish("view", action="close")
    return f"Closed {was}." if was else "Nothing was open; the screen is back to the assistant."


def control_view(action: str) -> str:
    if action not in CONTROL_ACTIONS:
        raise safety.ToolError(f"Unknown view action '{action}'. "
                               f"Use one of: {', '.join(CONTROL_ACTIONS)}.")
    with _lock:
        shown = _on_screen
    if shown is None:
        raise safety.ToolError("Nothing is open on the projector right now.")
    ui_events.publish("view_control", op=action)
    return f"Done: {action.replace('_', ' ')}."
