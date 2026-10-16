"""Decide whether the assistant is healthy, and prove it to systemd and the UI.

A crashed process is easy to detect: it exits. A HUNG one is not — it keeps
its PID, holds the GPIO pins and the microphone, and simply never answers
again. That is the failure the restart button was built for. This module
lets systemd catch it automatically: a background thread pings the systemd
watchdog only while the assistant shows signs of life, and stops pinging
when it does not, so systemd kills and restarts it.

What counts as "signs of life" is progress, not elapsed time:

  turn        a triggered turn must keep moving. Every stage (recording,
              transcription, each LLM round, each chunk of speech) reports
              progress. A long spoken answer is fine; ninety seconds with
              no progress at all is not, because every network call already
              has its own timeout shorter than that.

  wake word   the always-listening thread reports every audio chunk it reads
              (~80 ms). If it goes quiet while it should be listening, it is
              stuck inside the audio driver and the assistant is deaf to
              "Hey Atlas" even though nothing has crashed.

The same thread publishes a "heartbeat" event, so the projected UI can say
"assistant offline" instead of showing a reassuring but stale panel.
"""
import threading
import time

from . import sd_notify, ui_events

# How long a turn may go without ANY progress before it counts as hung.
TURN_STALL_S = 90.0
# How long the wake-word loop may go without reading a chunk. It reads every
# ~80 ms when listening and polls every 0.2 s while a turn holds the mic.
WAKE_WORD_STALL_S = 30.0
HEARTBEAT_S = 5.0


class Liveness:
    def __init__(self, turn_stall_s: float = TURN_STALL_S,
                 wake_word_stall_s: float = WAKE_WORD_STALL_S):
        self.turn_stall_s = turn_stall_s
        self.wake_word_stall_s = wake_word_stall_s
        self._lock = threading.Lock()
        self._turn_progress: float | None = None   # None = no turn running
        self._wake_word_progress: float | None = None  # None = not watched
        self._unhealthy_reason = ""
        self._thread: threading.Thread | None = None

    # --- reported by the rest of the assistant --------------------------
    def turn_started(self) -> None:
        with self._lock:
            self._turn_progress = time.monotonic()

    def turn_progress(self) -> None:
        with self._lock:
            if self._turn_progress is not None:
                self._turn_progress = time.monotonic()

    def turn_finished(self) -> None:
        with self._lock:
            self._turn_progress = None

    def wake_word_progress(self) -> None:
        """Called per audio chunk; must stay cheap (one float store)."""
        self._wake_word_progress = time.monotonic()

    # --- evaluation -------------------------------------------------------
    def healthy(self) -> bool:
        now = time.monotonic()
        with self._lock:
            turn = self._turn_progress
        wake = self._wake_word_progress
        if turn is not None and now - turn > self.turn_stall_s:
            self._unhealthy_reason = (
                f"turn made no progress for {now - turn:.0f} s")
            return False
        if wake is not None and now - wake > self.wake_word_stall_s:
            self._unhealthy_reason = (
                f"wake-word listener stalled for {now - wake:.0f} s")
            return False
        return True

    def start(self) -> None:
        """Start the heartbeat thread. Safe to call once."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="liveness")
        self._thread.start()

    def _run(self) -> None:
        interval = HEARTBEAT_S
        systemd_interval = sd_notify.watchdog_interval_s()
        if systemd_interval:
            interval = min(interval, systemd_interval)
        reported = False
        while True:
            if self.healthy():
                sd_notify.notify("WATCHDOG=1")
                ui_events.publish("heartbeat")
                reported = False
            elif not reported:
                # Say why once. The silence that follows is deliberate: it is
                # what makes systemd restart the process.
                print(f"⚠️ Assistant unhealthy: {self._unhealthy_reason}. "
                      "Withholding the watchdog ping so systemd restarts it.",
                      flush=True)
                reported = True
            time.sleep(interval)
