"""Path allowlisting for AI-callable tools.

Every tool that touches the filesystem resolves its argument through
`safe_path()` (reading) or `create_text()` (writing) first. Nothing else is
trusted: tool arguments arrive from a language model acting on speech, so
they are untrusted input in the same sense that a web form is.

Two separate guarantees:

  containment  the resolved path must sit under ALLOWED_ROOT (the project)
               or WORKSPACE_ROOT (the user's workspace). Resolution happens
               *before* the check and follows symlinks, so a symlink inside
               either root pointing at /etc cannot be used to escape — the
               resolved target is what gets tested.

  denial       some paths inside the roots are still off limits. .env is the
               important one: it holds the OpenAI and Groq keys and lives in
               the project directory, so "read-only access to the project"
               would otherwise mean "can read the keys aloud". Denied by
               path rule, not by hoping the model doesn't ask.

Scope decisions:
  2026-09-17 (owner)  ~/sws only, read-only.
  2026-10-01 (owner)  read the project; WRITE only into the workspace
                      (~/SWS_Workspace, outside git). Writing only ever
                      CREATES a new file: no overwrite, no delete, no rename.
                      With nothing destructive possible, no confirmation gate
                      is needed yet — one must be added before any tool that
                      can destroy or replace data.

Paths are shown to the user (and the model) relative to their root, with the
workspace prefixed "workspace/", e.g. "workspace/notes/parts_to_order.md".
The model passes those same strings back, so they resolve unambiguously.
"""
import os
import pathlib
import re

ALLOWED_ROOT = pathlib.Path(
    os.environ.get("TOOLS_ALLOWED_ROOT", "/home/swspi/sws")
).resolve()

WORKSPACE_ROOT = pathlib.Path(
    os.environ.get("TOOLS_WORKSPACE_ROOT", "~/SWS_Workspace")
).expanduser().resolve()
WORKSPACE_PREFIX = "workspace"
WORKSPACE_DIRS = ("notes", "documents", "schematics")

# Matched against any component of the path relative to the root.
DENIED_NAMES = {
    ".env",              # API keys
    ".git",              # object store; noise, and can contain history of .env
    ".venv",             # thousands of dependency files, pure noise
    "__pycache__",
    "node_modules",
}

# Matched against the file suffix. Reading these as text is meaningless and
# would flood the model's context with binary.
DENIED_SUFFIXES = {
    ".wav", ".mp3", ".raw", ".pcm", ".pyc", ".onnx", ".so", ".bin",
}

MAX_READ_BYTES = 64 * 1024
MAX_WRITE_BYTES = 64 * 1024
MAX_NAME_CHARS = 80


def is_denied_name(name: str) -> bool:
    """True if a single path component is off limits.

    Any name starting with ".env" counts, not just ".env" itself: a backup or
    variant copy (.env.bak, .env.local) holds the same keys, and an exact-name
    rule would let the model read it.
    """
    return name in DENIED_NAMES or name.startswith(".env")


class ToolError(Exception):
    """Raised for a refused or impossible tool call.

    Carries a message meant to be spoken back to the user and fed to the
    model, so it should explain the refusal rather than just failing.
    """


def ensure_workspace() -> pathlib.Path:
    """Create the workspace and its standard folders if missing."""
    for sub in WORKSPACE_DIRS:
        (WORKSPACE_ROOT / sub).mkdir(parents=True, exist_ok=True)
    return WORKSPACE_ROOT


def _root_of(resolved: pathlib.Path) -> pathlib.Path | None:
    """Which allowed root contains this resolved path, if any.

    The workspace is checked first: it is the more specific root if it was
    ever configured to live inside the project.
    """
    for root in (WORKSPACE_ROOT, ALLOWED_ROOT):
        if resolved == root or root in resolved.parents:
            return root
    return None


def safe_path(user_path: str, must_exist: bool = True) -> pathlib.Path:
    """Resolve `user_path` and confirm it may be read. Raises ToolError."""
    if not user_path or not str(user_path).strip():
        raise ToolError("No path given.")

    text = str(user_path).strip()
    parts = pathlib.PurePosixPath(text).parts
    if parts and parts[0] == WORKSPACE_PREFIX:
        candidate = WORKSPACE_ROOT.joinpath(*parts[1:])
    else:
        candidate = pathlib.Path(text).expanduser()
        if not candidate.is_absolute():
            candidate = ALLOWED_ROOT / candidate

    # strict=False so a non-existent path still normalises (for the clearer
    # "does not exist" message below rather than an OSError).
    resolved = candidate.resolve(strict=False)

    root = _root_of(resolved)
    if root is None:
        raise ToolError(
            "Access denied: that path is outside the project and the "
            "workspace."
        )

    for part in resolved.relative_to(root).parts:
        if is_denied_name(part):
            raise ToolError(
                f"Access denied: '{part}' is excluded. It holds credentials "
                f"or build artefacts, not project content."
            )

    if must_exist and not resolved.exists():
        raise ToolError(f"Not found: {_display(resolved)}")

    return resolved


def is_readable_text(path: pathlib.Path) -> bool:
    return path.suffix.lower() not in DENIED_SUFFIXES


def iter_project_files(root: pathlib.Path | None = None):
    """Walk the project, skipping denied directories entirely.

    Pruning in-place during os.walk matters: descending into .venv and then
    filtering afterwards would take seconds and allocate thousands of paths
    for a result that is always discarded.
    """
    base = root or ALLOWED_ROOT
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if not is_denied_name(d)]
        for name in filenames:
            if is_denied_name(name):
                continue
            yield pathlib.Path(dirpath) / name


def iter_workspace_files():
    """Walk the workspace (empty if it does not exist yet)."""
    if WORKSPACE_ROOT.is_dir():
        yield from iter_project_files(WORKSPACE_ROOT)


def _display(path: pathlib.Path) -> str:
    """Path relative to its root, for output the user will hear."""
    for root, prefix in ((WORKSPACE_ROOT, WORKSPACE_PREFIX), (ALLOWED_ROOT, "")):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        rel_text = "" if str(rel) == "." else str(rel)
        if prefix:
            return f"{prefix}/{rel_text}".rstrip("/")
        return rel_text or "."
    return str(path)


display = _display


# --- writing (workspace only) ----------------------------------------------

_UNSAFE_CHARS = re.compile(r"[^\w\-. ]", re.UNICODE)


def sanitize_filename(name: str, allowed_exts: set[str], default_ext: str) -> str:
    """Turn a model-supplied name into a safe single filename.

    Only the last path component survives (no folders, no ".."), anything
    but letters, digits, '-', '_', '.' and spaces is dropped (Unicode letters
    stay, so Arabic names work), spaces become '_', leading dots go (no
    hidden files, no ".env"), and the extension must be on the allowlist —
    a missing one gets `default_ext`.
    """
    base = re.split(r"[\\/]", str(name or "").strip())[-1]
    base = _UNSAFE_CHARS.sub("", base).strip().replace(" ", "_").lstrip(".")
    if not base:
        raise ToolError("That file name is empty once unsafe characters are removed.")
    stem, dot, ext = base.rpartition(".")
    if not dot or not stem:
        stem, ext = base, default_ext.lstrip(".")
    ext = "." + ext.lower()
    if ext not in allowed_exts:
        raise ToolError(
            f"I can only create {', '.join(sorted(allowed_exts))} files here, "
            f"not {ext}."
        )
    stem = stem[:MAX_NAME_CHARS].rstrip("._") or "untitled"
    if is_denied_name(stem):
        raise ToolError(f"'{stem}' is not an allowed file name.")
    return stem + ext


def create_text(subdir: str, filename: str, content: str,
                allowed_exts: set[str], default_ext: str) -> pathlib.Path:
    """Create a NEW text file in WORKSPACE_ROOT/subdir. Never overwrites.

    A name that is taken gets "-2", "-3", ... appended. The file is opened
    with O_EXCL ("x" mode), so even a race with another writer cannot make
    this replace an existing file.
    """
    if subdir not in WORKSPACE_DIRS:
        raise ToolError(f"Unknown workspace folder '{subdir}'.")
    data = str(content or "")
    if len(data.encode("utf-8")) > MAX_WRITE_BYTES:
        raise ToolError(f"That is more than {MAX_WRITE_BYTES // 1024} KB of text; "
                        "please make it shorter.")
    folder = ensure_workspace() / subdir
    name = sanitize_filename(filename, allowed_exts, default_ext)
    stem, ext = name[: -len(pathlib.Path(name).suffix)], pathlib.Path(name).suffix
    for n in range(1, 1000):
        candidate = folder / (name if n == 1 else f"{stem}-{n}{ext}")
        try:
            with open(candidate, "x", encoding="utf-8") as f:
                f.write(data)
            return candidate
        except FileExistsError:
            continue
    raise ToolError("Too many files with that name already exist.")
