"""Save schematic revisions: <folder>/<slug>/rN.json (spec) + rN.svg.

Every change is a NEW revision; nothing is ever overwritten (owner decision
2026-10-01, see tools/safety.py). Files are opened in exclusive-create mode,
so even two saves racing for the same revision number cannot clobber each
other: the loser just takes the next number.

The JSON spec is what "change R2 to 10k" edits: the next revision starts from
the previous one's inputs.
"""
import json
import pathlib
import re

_REV = re.compile(r"r(\d+)\.json")


def slug(title: str) -> str:
    """A folder name from a title: letters (any script), digits, '-', '_'."""
    s = re.sub(r"[^\w\-]+", "_", str(title or "").strip(), flags=re.UNICODE)
    return s.strip("_.")[:60] or "schematic"


def _revisions(folder: pathlib.Path) -> list[tuple[int, pathlib.Path]]:
    revs = []
    for p in folder.glob("r*.json"):
        m = _REV.fullmatch(p.name)
        if m:
            revs.append((int(m.group(1)), p))
    return sorted(revs)


def save(root: pathlib.Path, spec: dict, svg: bytes) -> tuple[pathlib.Path, int]:
    """Save the next revision. Returns (svg path, revision number)."""
    folder = root / slug(spec["title"])
    folder.mkdir(parents=True, exist_ok=True)
    for _ in range(1000):
        revs = _revisions(folder)
        n = (revs[-1][0] if revs else 0) + 1
        record = dict(spec, revision=n)
        try:
            with open(folder / f"r{n}.json", "x", encoding="utf-8") as f:
                json.dump(record, f, indent=2, ensure_ascii=False)
        except FileExistsError:
            continue
        svg_path = folder / f"r{n}.svg"
        with open(svg_path, "xb") as f:
            f.write(svg)
        return svg_path, n
    raise RuntimeError("could not allocate a revision number")


def latest(root: pathlib.Path, name: str = "") -> tuple[dict, pathlib.Path] | None:
    """The newest revision of the schematic called `name` ('' = any)."""
    if not root.is_dir():
        return None
    folders = [p for p in root.iterdir() if p.is_dir() and _revisions(p)]
    if name and name.strip():
        want = slug(name).lower()
        exact = [p for p in folders if p.name.lower() == want]
        folders = exact or [p for p in folders if want in p.name.lower()]
    if not folders:
        return None
    newest = max(folders, key=lambda p: _revisions(p)[-1][1].stat().st_mtime)
    rev_json = _revisions(newest)[-1][1]
    return json.loads(rev_json.read_text(encoding="utf-8")), rev_json.with_suffix(".svg")
