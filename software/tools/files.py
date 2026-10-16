"""Read-only file tools callable by the assistant.

Every return value is a short string, because it gets spoken aloud and fed
back into the model's context. That shapes the design more than it might
look: results are capped, truncation is stated rather than silent, and paths
are relative to the project root so the user hears "software/common/mic_stream.py"
rather than a full absolute path read out character by character.

All filesystem access goes through safety.safe_path — see that module for the
containment and denial rules.
"""
import pathlib
import subprocess

from . import safety

MAX_RESULTS = 25
MAX_READ_LINES = 200


def find_file(name_fragment: str, limit: int = MAX_RESULTS) -> str:
    """Find project files whose name contains `name_fragment`."""
    if not name_fragment or not name_fragment.strip():
        raise safety.ToolError("Give me part of a filename to look for.")

    needle = name_fragment.lower().strip()
    # Project and workspace both: "find my note about resistors" is as likely
    # as "where is the mic code".
    hits = [
        p for source in (safety.iter_project_files(), safety.iter_workspace_files())
        for p in source
        if needle in p.name.lower()
    ]
    if not hits:
        return f"No file matching '{name_fragment}' in the project."

    hits.sort(key=lambda p: (len(p.name), str(p)))
    shown = hits[:limit]
    lines = [safety.display(p) for p in shown]
    out = f"{len(hits)} match(es) for '{name_fragment}':\n" + "\n".join(lines)
    if len(hits) > limit:
        out += f"\n(showing first {limit})"
    return out


def list_directory(path: str = ".") -> str:
    """List the contents of a project directory."""
    target = safety.safe_path(path)
    if not target.is_dir():
        raise safety.ToolError(f"{safety.display(target)} is a file, not a directory.")

    entries = []
    for child in sorted(target.iterdir(), key=lambda c: (c.is_file(), c.name)):
        if safety.is_denied_name(child.name):
            continue
        if child.is_dir():
            entries.append(f"{child.name}/")
        else:
            entries.append(f"{child.name} ({child.stat().st_size} bytes)")

    if not entries:
        return f"{safety.display(target)} is empty."
    return f"{safety.display(target)}:\n" + "\n".join(entries)


def read_file(path: str, max_lines: int = MAX_READ_LINES) -> str:
    """Read a text file from the project."""
    target = safety.safe_path(path)
    if target.is_dir():
        raise safety.ToolError(
            f"{safety.display(target)} is a directory — use list_directory."
        )
    if not safety.is_readable_text(target):
        raise safety.ToolError(
            f"{safety.display(target)} is a binary file ({target.suffix}); "
            f"reading it as text would not be useful."
        )
    if target.stat().st_size > safety.MAX_READ_BYTES:
        raise safety.ToolError(
            f"{safety.display(target)} is "
            f"{target.stat().st_size // 1024}KB, too large to read in full. "
            f"Use search_code to find the relevant part."
        )

    try:
        text = target.read_text(errors="replace")
    except OSError as e:
        raise safety.ToolError(f"Could not read {safety.display(target)}: {e}")

    lines = text.splitlines()
    if len(lines) > max_lines:
        body = "\n".join(lines[:max_lines])
        return (f"{safety.display(target)} (first {max_lines} of "
                f"{len(lines)} lines):\n{body}")
    return f"{safety.display(target)} ({len(lines)} lines):\n{text}"


def search_code(query: str, limit: int = MAX_RESULTS) -> str:
    """Search the project's text files for `query`."""
    if not query or not query.strip():
        raise safety.ToolError("Give me something to search for.")

    # grep rather than a Python scan: it is dramatically faster over a tree
    # this size and already handles binary detection. Arguments are passed as
    # a list with no shell, so the query cannot inject anything.
    cmd = [
        "grep", "-rniI", "--max-count=3",
        *(f"--exclude-dir={d}" for d in safety.DENIED_NAMES),
        "--exclude=.env*", "--exclude-dir=.env*",
        "-e", query,
        str(safety.ALLOWED_ROOT),
        *([str(safety.WORKSPACE_ROOT)] if safety.WORKSPACE_ROOT.is_dir() else []),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        raise safety.ToolError("Search timed out.")

    # grep exits 1 for "no matches", which is not an error here.
    if result.returncode not in (0, 1):
        raise safety.ToolError(f"Search failed: {result.stderr[:200]}")

    raw = [ln for ln in result.stdout.splitlines() if ln.strip()]
    if not raw:
        return f"No matches for '{query}'."

    lines = []
    for entry in raw[:limit]:
        path_part, _, rest = entry.partition(":")
        try:
            rel = safety.display(pathlib.Path(path_part))
        except Exception:
            rel = path_part
        lines.append(f"{rel}:{rest.strip()[:160]}")

    out = f"{len(raw)} match(es) for '{query}':\n" + "\n".join(lines)
    if len(raw) > limit:
        out += f"\n(showing first {limit})"
    return out


def project_status() -> str:
    """Summarise the project's git state and layout."""
    def git(*args: str) -> str:
        r = subprocess.run(
            ["git", "-C", str(safety.ALLOWED_ROOT), *args],
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout.strip() if r.returncode == 0 else ""

    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    last = git("log", "-1", "--format=%h %s") or "no commits"
    dirty = git("status", "--porcelain")
    changed = len([ln for ln in dirty.splitlines() if ln.strip()])

    py_files = sum(
        1 for p in safety.iter_project_files() if p.suffix == ".py"
    )

    parts = [
        f"Branch: {branch}",
        f"Last commit: {last}",
        f"Uncommitted changes: {changed}" if changed else "Working tree clean",
        f"Python files: {py_files}",
    ]
    return "\n".join(parts)
