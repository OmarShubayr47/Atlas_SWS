"""Create files in the user's workspace, and list what is there.

Owner decision 2026-10-01: the assistant may CREATE files, only inside
~/SWS_Workspace (outside git), and never overwrite or delete anything. The
rules live in safety.create_text; this module is the voice-facing layer.
Every new file is shown on the projector straight away, so the user sees
exactly what was written.

Files are created as data only. A .py file written here is text in a
folder — nothing in the assistant ever runs it.
"""
import pathlib

from . import safety, view

NOTE_EXTS = {".md", ".txt"}
DOCUMENT_EXTS = {".md", ".txt", ".csv", ".py", ".json"}


def create_note(title: str, text: str) -> str:
    title = (title or "").strip() or "Note"
    body = f"# {title}\n\n{(text or '').strip()}\n"
    path = safety.create_text("notes", title, body, NOTE_EXTS, ".md")
    shown = view.show(path)
    return f"Saved the note as {safety.display(path)}. {shown}"


def create_text_file(filename: str, content: str) -> str:
    path = safety.create_text("documents", filename, content or "",
                              DOCUMENT_EXTS, ".txt")
    view.show(path)
    return f"Created {safety.display(path)} and put it on the screen."


def _listable(path: pathlib.Path) -> bool:
    # Schematic revisions are saved as a JSON spec plus an SVG drawing; the
    # drawing is the thing to show, the spec is for editing.
    if path.suffix.lower() == ".json" and "schematics" in path.parts:
        return False
    return view.kind_for(path) is not None


def show_workspace(folder: str = "") -> str:
    root = safety.ensure_workspace()
    folder = (folder or "").strip().strip("/")
    if folder and folder not in safety.WORKSPACE_DIRS:
        raise safety.ToolError(
            f"The workspace folders are {', '.join(safety.WORKSPACE_DIRS)}.")
    base = root / folder if folder else root
    files = [p for p in safety.iter_project_files(base) if _listable(p)]
    # One entry per schematic: its newest revision. Older ones stay on disk.
    newest: dict[pathlib.Path, pathlib.Path] = {}
    others = []
    for p in files:
        if "schematics" in p.relative_to(root).parts[:1] and p.stem[1:].isdigit():
            best = newest.get(p.parent)
            if best is None or int(p.stem[1:]) > int(best.stem[1:]):
                newest[p.parent] = p
        else:
            others.append(p)
    files = others + list(newest.values())
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    title = f"workspace/{folder}" if folder else "workspace"
    view.show_list(title, files)
    if not files:
        return f"{title} is empty so far."
    lines = [f"{i}. {safety.display(p)}"
             for i, p in enumerate(files[:view.MAX_LIST_ITEMS], start=1)]
    more = (f"\n(showing the newest {view.MAX_LIST_ITEMS} of {len(files)})"
            if len(files) > view.MAX_LIST_ITEMS else "")
    return f"{len(files)} file(s) in {title}, newest first:\n" + "\n".join(lines) + more
