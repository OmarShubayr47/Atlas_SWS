"""Phase 3: workspace safety, file tools, view events and the UI server's
/file and /pdfpage endpoints. Uses temporary project/workspace roots."""
import json
import os
import pathlib
import threading
import urllib.error
import urllib.request

import pytest

from tools import registry, safety, view, workspace

MINIMAL_PDF = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
               b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
               b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
               b"trailer<</Size 4/Root 1 0 R>>\n%%EOF\n")


@pytest.fixture
def roots(tmp_path, monkeypatch):
    project = tmp_path / "sws"
    work = tmp_path / "SWS_Workspace"
    (project / "docs").mkdir(parents=True)
    (project / "docs" / "status.md").write_text("# Status\nall good\n")
    (project / ".env").write_text("OPENAI_API_KEY=not-a-real-key\n")
    monkeypatch.setattr(safety, "ALLOWED_ROOT", project.resolve())
    monkeypatch.setattr(safety, "WORKSPACE_ROOT", work.resolve())
    return project.resolve(), work.resolve()


@pytest.fixture
def events(monkeypatch):
    seen = []
    # Same signature as the real ui_events.publish(event_type, **fields):
    # events carry their own "kind" field, so the name must not clash.
    monkeypatch.setattr(view.ui_events, "publish",
                        lambda event_type, **f: seen.append({"type": event_type, **f}))
    monkeypatch.setattr(view, "_on_screen", None)
    return seen


# --- safety --------------------------------------------------------------------

def test_workspace_paths_resolve_and_display(roots):
    project, work = roots
    safety.ensure_workspace()
    note = work / "notes" / "a.md"
    note.write_text("x")
    assert safety.safe_path("workspace/notes/a.md") == note
    assert safety.display(note) == "workspace/notes/a.md"
    assert safety.safe_path("docs/status.md") == project / "docs" / "status.md"
    assert safety.display(project / "docs" / "status.md") == "docs/status.md"


@pytest.mark.parametrize("bad", [
    ".env", "docs/../.env", "workspace/../sws/.env", "/etc/passwd",
    "../../etc/passwd", "workspace/../../etc/passwd",
])
def test_reads_outside_or_denied_are_refused(roots, bad):
    with pytest.raises(safety.ToolError):
        safety.safe_path(bad)


def test_symlink_escape_is_refused(roots):
    project, work = roots
    safety.ensure_workspace()
    (work / "notes" / "escape").symlink_to("/etc")
    with pytest.raises(safety.ToolError):
        safety.safe_path("workspace/notes/escape/passwd")


@pytest.mark.parametrize("name,expected", [
    ("Parts to order", "Parts_to_order.md"),
    ("../../etc/passwd", "passwd.md"),
    (".env", "env.md"),
    ("قائمة القطع", "قائمة_القطع.md"),
    ("notes.TXT", "notes.txt"),
    ("a/b\\c.md", "c.md"),
])
def test_sanitize_filename(name, expected):
    assert safety.sanitize_filename(name, {".md", ".txt"}, ".md") == expected


def test_sanitize_rejects_bad_extension_and_empty():
    with pytest.raises(safety.ToolError):
        safety.sanitize_filename("run.sh", {".md"}, ".md")
    with pytest.raises(safety.ToolError):
        safety.sanitize_filename("///", {".md"}, ".md")


def test_create_never_overwrites(roots):
    _, work = roots
    a = safety.create_text("notes", "todo", "one", {".md"}, ".md")
    b = safety.create_text("notes", "todo", "two", {".md"}, ".md")
    assert (a.name, b.name) == ("todo.md", "todo-2.md")
    assert a.read_text() == "one" and b.read_text() == "two"


def test_create_refuses_huge_content_and_unknown_folder(roots):
    with pytest.raises(safety.ToolError):
        safety.create_text("notes", "big", "x" * (safety.MAX_WRITE_BYTES + 1), {".md"}, ".md")
    with pytest.raises(safety.ToolError):
        safety.create_text("../evil", "x", "y", {".md"}, ".md")


# --- tools and view events --------------------------------------------------------

def test_create_note_writes_and_shows(roots, events):
    _, work = roots
    msg = workspace.create_note("Resistors", "Order 10k and 4.7k")
    text = (work / "notes" / "Resistors.md").read_text()
    assert text == "# Resistors\n\nOrder 10k and 4.7k\n"
    assert "workspace/notes/Resistors.md" in msg
    assert events[-1] == {"type": "view", "action": "open", "kind": "text",
                          "path": "workspace/notes/Resistors.md", "title": "Resistors.md"}


def test_open_file_kinds_and_errors(roots, events):
    project, _ = roots
    assert "Showing docs/status.md" in view.open_file("docs/status.md")
    (project / "docs" / "t.pdf").write_bytes(MINIMAL_PDF)
    out = view.open_file("docs/t.pdf")
    assert events[-1]["kind"] == "pdf" and events[-1]["pages"] == 1 and "1 page" in out
    (project / "docs" / "x.xlsx").write_bytes(b"PK")
    with pytest.raises(safety.ToolError):
        view.open_file("docs/x.xlsx")
    assert "Showing the folder docs" in view.open_file("docs")
    assert events[-1]["kind"] == "list"


def test_control_needs_something_open(roots, events):
    with pytest.raises(safety.ToolError):
        view.control_view("zoom_in")
    view.open_file("docs/status.md")
    assert view.control_view("zoom_in") == "Done: zoom in."
    assert events[-1] == {"type": "view_control", "op": "zoom_in"}
    with pytest.raises(safety.ToolError):
        view.control_view("rm -rf")
    assert "Closed" in view.close_view()


def test_show_workspace_lists_newest_first(roots, events):
    workspace.create_note("first", "a")
    workspace.create_text_file("parts.csv", "part,qty\nR1,2\n")
    out = workspace.show_workspace()
    assert out.splitlines()[1].endswith("documents/parts.csv")
    assert [i["n"] for i in events[-1]["items"]] == [1, 2]


def test_registry_dispatch_and_schemas(roots, events):
    names = {t["function"]["name"] for t in registry.chat_schemas()}
    assert {"open_file", "control_view", "close_view", "show_workspace",
            "create_note", "create_text_file"} <= names
    json.dumps(registry.chat_schemas())
    out = registry.dispatch("create_note", json.dumps({"title": "x", "text": "y"}))
    assert "workspace/notes/x.md" in out
    assert "can only create" in registry.dispatch(
        "create_text_file", {"filename": "evil.sh", "content": "rm"})


# --- UI server endpoints -----------------------------------------------------------

@pytest.fixture
def server(roots, tmp_path, monkeypatch):
    from http.server import ThreadingHTTPServer
    import ui.server as srv
    monkeypatch.setattr(srv, "PDF_CACHE", tmp_path / "cache")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", srv
    httpd.shutdown()


def get(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=30) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def test_server_file_endpoint_enforces_safety(server):
    base, _ = server
    status, headers, body = get(f"{base}/file?path=docs/status.md")
    assert status == 200 and body.startswith(b"# Status")
    assert "sandbox" in headers["Content-Security-Policy"]
    for bad in (".env", "../../etc/passwd", "/etc/passwd"):
        status, _, body = get(f"{base}/file?path={urllib.request.quote(bad)}")
        assert status == 403, bad
        assert b"not-a-real-key" not in body


def test_server_renders_pdf_page(server, roots):
    base, _ = server
    project, _ = roots
    (project / "docs" / "t.pdf").write_bytes(MINIMAL_PDF)
    status, headers, body = get(f"{base}/pdfpage?path=docs/t.pdf&page=1")
    assert status == 200 and headers["Content-Type"] == "image/png"
    assert body[:8] == b"\x89PNG\r\n\x1a\n"


def test_server_page_csp_and_no_replay_of_view_control(server):
    base, srv = server
    status, headers, _ = get(f"{base}/")
    assert status == 200 and "script-src 'self'" in headers["Content-Security-Policy"]
    srv.HUB.publish({"type": "view_control", "op": "zoom_in"})
    srv.HUB.publish({"type": "view", "action": "close"})
    latest = {e["type"] for e in srv.HUB.snapshot()[0]}
    assert "view" in latest and "view_control" not in latest
