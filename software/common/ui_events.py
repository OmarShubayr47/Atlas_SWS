"""Fire-and-forget status events from the assistant to the projected UI.

The assistant must never wait on, or fail because of, the display. So events
go into a bounded queue drained by a background thread, each POST has a short
timeout, and every error is swallowed. If the UI server is not running, events
are simply dropped — the panel catches up from the next one.

    ui_events.publish("state", state="listening")
    ui_events.publish("transcript", text="what does amp_enable do?")

Set UI_EVENTS=0 to switch it off entirely.
"""
import json
import os
import queue
import threading
import time
import urllib.request

URL = f"http://127.0.0.1:{os.environ.get('UI_PORT', '8765')}/event"
ENABLED = os.environ.get("UI_EVENTS", "1").lower() not in ("0", "false", "")
TIMEOUT_S = 0.5

# No proxy for loopback: an http_proxy set in the environment would otherwise
# route these requests off the machine and fail in a confusing way.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_queue: queue.Queue = queue.Queue(maxsize=100)
_lock = threading.Lock()
_started = False


def _worker() -> None:
    while True:
        event = _queue.get()
        try:
            req = urllib.request.Request(
                URL, data=json.dumps(event).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            _opener.open(req, timeout=TIMEOUT_S).close()
        except Exception:
            pass  # UI down or slow: the assistant carries on regardless


def publish(event_type: str, **fields) -> None:
    global _started
    if not ENABLED:
        return
    if not _started:
        with _lock:
            if not _started:
                threading.Thread(target=_worker, daemon=True).start()
                _started = True
    try:
        _queue.put_nowait({"type": event_type, "ts": time.time(), **fields})
    except queue.Full:
        pass  # UI badly behind; dropping is better than blocking the assistant
