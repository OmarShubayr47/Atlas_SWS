"""Local server for the projected interface (Chromium kiosk).

Two jobs, both on 127.0.0.1 only:
    POST /event    the voice assistant announces what it is doing
    GET  /events   the browser subscribes (Server-Sent Events) and redraws

A separate process from the assistant for the same reason as the restart
button: the UI crashing, or simply not being started, must never take the
assistant down with it. The assistant fires events and forgets them.

Server-Sent Events rather than WebSockets: a status panel only needs
server -> browser. SSE is plain HTTP, needs nothing beyond the standard
library, and the browser's EventSource reconnects by itself if this server
restarts. When touch needs to send actions back, the browser can POST.

Late joiners: the kiosk can (re)load at any moment — restart, projector power
cycle. So the latest event of each type is kept and replayed first, instead of
showing a blank panel until the next event happens to arrive.

Usage:
    python software/ui/server.py        (normally started by run_kiosk.sh)
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SOFTWARE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOFTWARE))
try:  # same .env as the assistant: UI_PORT, TOOLS_WORKSPACE_ROOT, ...
    from dotenv import load_dotenv
    load_dotenv(SOFTWARE.parent / ".env", override=True)
except ImportError:
    pass

# The viewer serves files with the SAME rules the assistant's tools use. The
# event that says "show X" is not trusted: the path is checked again here.
from tools import safety, view  # noqa: E402

# Loopback only, deliberately not configurable: nothing off this Pi should be
# able to drive what is projected on the desk.
HOST = "127.0.0.1"
PORT = int(os.environ.get("UI_PORT", "8765"))
STATIC = (pathlib.Path(__file__).resolve().parent / "static").resolve()
PDF_CACHE = SOFTWARE.parent / "scratch" / "viewer_cache"
PDF_CACHE_MAX_FILES = 200
MAX_BODY = 16 * 1024
KEEPALIVE_S = 15
EVENT_TYPES = {"state", "transcript", "reply", "tool", "volume", "error",
               "heartbeat", "restart", "view", "view_control"}
# Momentary events: replaying the last one to a kiosk that (re)loads later
# would show a stale "keep holding to reboot" banner or re-apply an old zoom,
# so they are only ever delivered live. ("view" IS replayed: a reloaded kiosk
# should come back showing the same document.)
NO_REPLAY = {"restart", "view_control"}
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml",
    ".png": "image/png",
}
IMAGE_TYPES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
}
# The page itself: only our own script and styles. Replies are LLM text and
# are only ever inserted with textContent, but this is the second fence.
PAGE_CSP = ("default-src 'self'; img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self'; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'")
# Served user files: inert even if opened directly as a document.
FILE_CSP = "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox"


class Hub:
    """Fan-out of events to every connected browser."""

    def __init__(self):
        self._cv = threading.Condition()
        self._seq = 0
        self._recent: list[dict] = []
        self._latest: dict[str, dict] = {}

    def publish(self, event: dict) -> None:
        with self._cv:
            self._seq += 1
            event["seq"] = self._seq
            self._recent.append(event)
            del self._recent[:-200]
            if event["type"] not in NO_REPLAY:
                self._latest[event["type"]] = event
            self._cv.notify_all()

    def snapshot(self) -> tuple[list[dict], int]:
        with self._cv:
            return sorted(self._latest.values(), key=lambda e: e["seq"]), self._seq

    def wait_after(self, seq: int, timeout: float) -> tuple[list[dict], int]:
        with self._cv:
            self._cv.wait_for(lambda: self._seq > seq, timeout=timeout)
            return [e for e in self._recent if e["seq"] > seq], self._seq


HUB = Hub()


class Handler(BaseHTTPRequestHandler):
    server_version = "sws-ui/1"

    def log_message(self, fmt, *args):
        pass  # SSE connections stay open for hours; per-request logs are noise

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path
        if path == "/health":
            return self._send(200, b"ok", "text/plain")
        if path == "/events":
            return self._stream()
        if path == "/file":
            return self._file(parse_qs(url.query))
        if path == "/pdfpage":
            return self._pdfpage(parse_qs(url.query))
        if path == "/":
            path = "/index.html"
        target = (STATIC / path.lstrip("/")).resolve()
        # Resolve first, then require it to be inside STATIC: blocks ../ tricks.
        if STATIC not in target.parents or not target.is_file():
            return self._send(404, b"not found", "text/plain")
        ctype = CONTENT_TYPES.get(target.suffix, "application/octet-stream")
        self._send(200, target.read_bytes(), ctype, {"Content-Security-Policy": PAGE_CSP})

    # --- the viewer's files ----------------------------------------------
    def _resolve(self, query: dict):
        """A viewable file from ?path=..., or None after sending an error."""
        try:
            target = safety.safe_path((query.get("path") or [""])[0])
        except safety.ToolError as e:
            self._send(403, str(e).encode(), "text/plain; charset=utf-8")
            return None
        if not target.is_file():
            self._send(404, b"not a file", "text/plain")
            return None
        return target

    def _file(self, query: dict) -> None:
        target = self._resolve(query)
        if target is None:
            return
        kind = view.kind_for(target)
        headers = {"Content-Security-Policy": FILE_CSP, "X-Content-Type-Options": "nosniff"}
        if kind == "text":
            if target.stat().st_size > view.MAX_TEXT_BYTES:
                return self._send(413, b"too large", "text/plain")
            return self._send(200, target.read_bytes(), "text/plain; charset=utf-8", headers)
        if kind == "image":
            return self._send(200, target.read_bytes(),
                              IMAGE_TYPES.get(target.suffix.lower(), "application/octet-stream"),
                              headers)
        self._send(415, b"not viewable here (PDFs: /pdfpage)", "text/plain")

    def _pdfpage(self, query: dict) -> None:
        """One PDF page as PNG, rendered by pdftoppm and cached in scratch/."""
        target = self._resolve(query)
        if target is None:
            return
        if view.kind_for(target) != "pdf":
            return self._send(415, b"not a PDF", "text/plain")
        try:
            page = max(1, int((query.get("page") or ["1"])[0]))
            dpi = min(200, max(72, int((query.get("dpi") or ["150"])[0])))
        except ValueError:
            return self._send(400, b"bad page or dpi", "text/plain")
        key = hashlib.sha1(
            f"{target}:{target.stat().st_mtime_ns}:{page}:{dpi}".encode()).hexdigest()
        PDF_CACHE.mkdir(parents=True, exist_ok=True)
        png = PDF_CACHE / f"{key}.png"
        if not png.is_file():
            tmp_base = PDF_CACHE / f"{key}.{threading.get_ident()}.tmp"
            try:
                subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-f", str(page),
                                "-l", str(page), "-singlefile", str(target), str(tmp_base)],
                               capture_output=True, timeout=60, check=True)
                # Atomic: two kiosk requests for the same page cannot see a
                # half-written image.
                os.replace(f"{tmp_base}.png", png)
            except (OSError, subprocess.SubprocessError) as e:
                return self._send(500, f"render failed: {e}".encode()[:300], "text/plain")
            self._prune_cache()
        self._send(200, png.read_bytes(), "image/png",
                   {"Content-Security-Policy": FILE_CSP, "X-Content-Type-Options": "nosniff"})

    @staticmethod
    def _prune_cache() -> None:
        files = sorted(PDF_CACHE.glob("*.png"), key=lambda p: p.stat().st_mtime)
        for old in files[:-PDF_CACHE_MAX_FILES]:
            try:
                old.unlink()
            except OSError:
                pass

    def do_POST(self):
        if urlparse(self.path).path != "/event":
            return self._send(404, b"not found", "text/plain")
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 < n <= MAX_BODY:
                raise ValueError("body missing or too large")
            event = json.loads(self.rfile.read(n))
            if not isinstance(event, dict) or event.get("type") not in EVENT_TYPES:
                raise ValueError(f"type must be one of {sorted(EVENT_TYPES)}")
        except ValueError as e:  # includes json.JSONDecodeError
            return self._send(400, str(e).encode(), "text/plain")
        event.setdefault("ts", time.time())
        HUB.publish(event)
        self._send(204, b"", "text/plain")

    def _send(self, code: int, body: bytes, ctype: str,
              headers: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _stream(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        events, seq = HUB.snapshot()
        try:
            for e in events:
                self._emit(e)
            while True:
                new, seq = HUB.wait_after(seq, KEEPALIVE_S)
                if not new:
                    # Comment line: keeps idle connections from being dropped.
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                for e in new:
                    self._emit(e)
        except (BrokenPipeError, ConnectionResetError):
            return  # browser went away; EventSource will reconnect if it can

    def _emit(self, event: dict) -> None:
        self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
        self.wfile.flush()


def main() -> int:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    httpd.daemon_threads = True
    print(f"UI server on http://{HOST}:{PORT}/  (static: {STATIC})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
