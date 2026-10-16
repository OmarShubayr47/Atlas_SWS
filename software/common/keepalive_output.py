"""A playback stream that never closes: silence while idle, speech on demand.

Why it exists: the Caiwei projector's HDMI audio drops the first several
seconds of every NEW audio stream (tested 2026-09-22: 12 s tones were heard,
4-5 s spoken replies were not heard at all). Opening aplay per reply, as the
amp path does, therefore loses whole replies. Keeping one stream open and
feeding it silence between replies means the projector unmutes once, at
startup, and stays that way.

Silence is paced by the clock, not by back-pressure. aplay reads from a pipe,
and a pipe holds ~64 KB — about 1.3 s of 24 kHz mono. Writing silence as fast
as the pipe accepts it would keep that much silence queued ahead of any
speech, delaying every reply by up to 1.3 s. Instead, silence is written only
while the stream is less than LEAD_S ahead of real time.

    out = KeepAliveOutput("plug:'hdmi:CARD=vc4hdmi0,DEV=0'", volume=vol)
    out.begin()              # a new reply starts
    out.write(pcm_chunk)     # speech: 24 kHz mono S16_LE, any chunk size
    out.drain()              # block until the speech has been played
    out.cancel()             # (from another thread) stop the reply now

Per-reply statistics (2026-10-01): spoken replies were reported cutting out
roughly every 0.5 s (owner, 2026-09-29), cause unknown. One hypothesis is
that the speech arrives from the network more slowly than it plays, so the
silence pacer — doing exactly its job — fills the holes with silence in the
MIDDLE of a reply. drain() therefore logs, for every reply, how long the
audio was, how long delivery took, the smallest lead seen, and how much
silence had to be inserted mid-reply. Non-zero gaps confirm that hypothesis;
zero gaps alongside audible cutouts rule it out and point downstream (ALSA,
HDMI, the projector), which is why aplay's own messages (xruns) are now
logged instead of being discarded.
"""
import subprocess
import threading
import time

import numpy as np

RATE = 24000          # TTS "pcm" response format: 24 kHz mono 16-bit
BYTES_PER_S = RATE * 2
LEAD_S = 0.15         # how far ahead of real time silence may run
TICK_S = 0.02         # silence granularity (20 ms)
# Audio still inside ALSA/the HDMI path after leaving the pipe. An ESTIMATE,
# not measured: drain() waits this long extra so "done" means heard.
OUTPUT_LATENCY_S = 0.3

# Soft limiter knee, as a fraction of full scale. Below it the signal passes
# untouched; above it peaks are rounded off smoothly towards full scale
# instead of hard-clipping.
LIMIT_KNEE = 0.8

# When aplay keeps dying (projector off, HDMI unplugged), back off instead of
# respawning it twice a second forever: 0.5 s, 1 s, 2 s ... capped at 30 s.
RESTART_MIN_S = 0.5
RESTART_MAX_S = 30.0
STABLE_S = 10.0       # a process that ran this long resets the backoff
LOG_REPEAT_S = 60.0   # the same message is printed at most once a minute


def apply_gain(pcm: bytes, gain_db: float) -> bytes:
    """Boost 16-bit mono PCM by gain_db with a soft limiter on the peaks.

    Why: TTS speech measured peak -15.4 dBFS, speech RMS -29.7 dBFS
    (2026-09-22) — about 15 dB of unused headroom, which made replies quiet
    on the projector even at its 100% volume. Memoryless (each sample
    independently), so arbitrary chunk boundaries cannot cause clicks.
    """
    if not gain_db or not pcm:
        return pcm
    x = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
    x *= 10 ** (gain_db / 20)
    mag = np.abs(x)
    over = mag > LIMIT_KNEE
    if over.any():
        span = 1.0 - LIMIT_KNEE
        mag[over] = LIMIT_KNEE + span * np.tanh((mag[over] - LIMIT_KNEE) / span)
        x = np.sign(x) * mag
    return (np.clip(x, -1.0, 32767 / 32768) * 32768).astype("<i2").tobytes()


class GainStage:
    """Turns arbitrary network chunks into whole, level-adjusted samples.

    Network chunks can split a 16-bit sample. If silence were inserted after
    an odd-length chunk, every later sample would be misaligned by one byte —
    loud static. The stray byte waits here for its partner instead.

    base_gain_db  fixed boost for this output (SPEECH_GAIN_DB on HDMI)
    volume        optional live level (common/speech_volume.SpeechVolume):
                  its gain_db() is read per chunk, so the knob takes effect
                  on the next chunk; None from it means write silence.
    """

    def __init__(self, base_gain_db: float = 0.0, volume=None):
        self.base_gain_db = base_gain_db
        self.volume = volume
        self._carry = b""

    def reset(self) -> None:
        self._carry = b""     # a lone trailing byte is not a sample

    def process(self, data: bytes) -> bytes:
        data = self._carry + data
        if len(data) % 2:
            data, self._carry = data[:-1], data[-1:]
        else:
            self._carry = b""
        if not data:
            return b""
        level = 0.0
        if self.volume is not None:
            level = self.volume.gain_db()
            if level is None:
                return bytes(len(data))      # mute: true digital silence
        # Gain AFTER alignment: it has to see whole samples.
        return apply_gain(data, self.base_gain_db + level)


class _RateLimitedLog:
    """Print a message, then hold back repeats of the same key for a while."""

    def __init__(self, every_s: float = LOG_REPEAT_S):
        self._every_s = every_s
        self._last: dict[str, float] = {}
        self._held: dict[str, int] = {}

    def __call__(self, key: str, message: str) -> None:
        now = time.monotonic()
        if now - self._last.get(key, float("-inf")) < self._every_s:
            self._held[key] = self._held.get(key, 0) + 1
            return
        held = self._held.pop(key, 0)
        suffix = f"  (+{held} similar in the last minute)" if held else ""
        print(message + suffix, flush=True)
        self._last[key] = now


class _ReplyStats:
    """What happened to one reply on its way to the speaker."""

    def __init__(self, now: float):
        self.t_first = self.t_last = now
        self.bytes = 0
        self.gap_s = 0.0
        self.gap_events = 0
        self.min_lead: float | None = None
        self._in_gap = False

    def speech(self, n_bytes: int, lead_before: float, now: float) -> None:
        # The lead before the FIRST chunk is just the idle silence lead, not
        # a property of this reply's delivery, so it is left out.
        if self.bytes:
            self.min_lead = (lead_before if self.min_lead is None
                             else min(self.min_lead, lead_before))
        self.bytes += n_bytes
        self.t_last = now
        self._in_gap = False

    def gap(self, seconds: float) -> None:
        self.gap_s += seconds
        if not self._in_gap:
            self.gap_events += 1
            self._in_gap = True

    def summary(self, cancelled: bool = False) -> str:
        audio_s = self.bytes / BYTES_PER_S
        lead = "n/a" if self.min_lead is None else f"{self.min_lead:.2f} s"
        tag = "  [CANCELLED]" if cancelled else ""
        return (f"🔈 Reply audio {audio_s:.2f} s, delivered over "
                f"{self.t_last - self.t_first:.2f} s, min lead {lead}, "
                f"gaps {self.gap_events} ({self.gap_s * 1000:.0f} ms){tag}")


class KeepAliveOutput:
    def __init__(self, pcm_device: str, gain_db: float = 0.0, volume=None):
        self._device = pcm_device
        self._stage = GainStage(gain_db, volume)
        self._lock = threading.Lock()
        self._proc = None
        self._t0 = 0.0        # wall clock at which byte 0 would have played
        self._written = 0     # bytes handed to aplay since _t0
        self._started_at = 0.0
        self._failures = 0
        self._next_start = 0.0
        self._discard = False  # set by cancel(): drop the rest of this reply
        self._reply: _ReplyStats | None = None
        self._log = _RateLimitedLog()
        with self._lock:
            self._start_locked()
        threading.Thread(target=self._silence_loop, daemon=True,
                         name="keepalive").start()

    # --- the aplay process ------------------------------------------------
    def _start_locked(self) -> None:
        try:
            self._proc = subprocess.Popen(
                ["aplay", "-D", self._device, "-t", "raw", "-f", "S16_LE",
                 "-r", str(RATE), "-c", "1", "-q", "-"],
                stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as e:
            self._proc = None
            self._schedule_restart_locked(f"could not start aplay: {e}")
            return
        threading.Thread(target=self._pump_stderr, args=(self._proc,),
                         daemon=True, name="aplay-stderr").start()
        self._started_at = self._t0 = time.monotonic()
        self._written = 0
        self._stage.reset()

    def _pump_stderr(self, proc) -> None:
        """Forward aplay's messages (xruns, open errors) to our log."""
        for raw in proc.stderr:      # ends at EOF, when aplay exits
            line = raw.decode(errors="replace").strip()
            if line:
                self._log("aplay:" + line[:48], f"🔈 aplay: {line}")

    def _kill_locked(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.kill()
            self._proc.wait(timeout=1)   # reap it: no zombies over months
        except Exception:
            pass
        self._proc = None

    def _schedule_restart_locked(self, reason: str) -> None:
        now = time.monotonic()
        lived = now - self._started_at
        self._failures = 1 if lived >= STABLE_S else self._failures + 1
        delay = min(RESTART_MAX_S, RESTART_MIN_S * 2 ** (self._failures - 1))
        self._next_start = now + delay
        self._log("restart", f"⚠️ keepalive output: {reason}; restarting in "
                             f"{delay:.1f} s (failure {self._failures})")
        self._kill_locked()

    def _lead(self) -> float:
        """Seconds of audio written beyond what should have played by now."""
        lead = self._written / BYTES_PER_S - (time.monotonic() - self._t0)
        if lead < 0:
            # Fell behind (writer stalled): re-anchor rather than trying to
            # "catch up" with a burst of silence.
            self._t0 = time.monotonic() - self._written / BYTES_PER_S
            lead = 0.0
        return lead

    def _write_locked(self, data: bytes) -> bool:
        if self._proc is None:
            return False
        try:
            self._proc.stdin.write(data)
            self._proc.stdin.flush()
        except (BrokenPipeError, ValueError, OSError):
            # aplay died (device gone, HDMI unplugged). Drop this chunk; the
            # silence loop starts a new process after the backoff delay.
            self._schedule_restart_locked("aplay exited")
            return False
        self._written += len(data)
        return True

    def _silence_loop(self) -> None:
        silence = bytes(int(BYTES_PER_S * TICK_S))
        while True:
            with self._lock:
                if self._proc is not None and self._proc.poll() is not None:
                    self._schedule_restart_locked(
                        f"aplay exited with code {self._proc.returncode}")
                if self._proc is None:
                    if time.monotonic() >= self._next_start:
                        self._start_locked()
                elif self._lead() < LEAD_S:
                    # Mid-reply, this silence is a hole in the speech.
                    if self._write_locked(silence) and self._reply is not None:
                        self._reply.gap(TICK_S)
            time.sleep(TICK_S / 2)

    # --- the reply API ----------------------------------------------------
    def begin(self) -> None:
        """A new reply starts: forget any earlier cancel and statistics."""
        with self._lock:
            self._discard = False
            self._reply = None
            self._stage.reset()

    def write(self, data: bytes) -> None:
        """Queue speech: 24 kHz mono S16_LE, any chunk size."""
        with self._lock:
            if self._discard:
                return
            data = self._stage.process(data)
            if not data:
                return
            now = time.monotonic()
            lead = self._lead()      # re-anchor first if idle time was lost
            if self._reply is None:
                self._reply = _ReplyStats(now)
            if self._write_locked(data):
                self._reply.speech(len(data), lead, now)

    def drain(self) -> None:
        """Block until everything written so far should have played."""
        with self._lock:
            self._stage.reset()
            stats, self._reply = self._reply, None
            if self._discard:
                return               # cancelled: nothing left to wait for
            remaining = self._lead()
        if stats is not None:
            print(stats.summary(), flush=True)
        time.sleep(remaining + OUTPUT_LATENCY_S)

    def cancel(self) -> None:
        """Stop the current reply now. Safe to call from any thread.

        Audio already handed to aplay (~1.5 s in its pipe and buffer) can only
        be dropped by killing aplay, so that is what this does — but only when
        a reply is actually playing. The silence loop's replacement process
        starts at once and is fed silence, so the projector has re-locked onto
        the stream well before the next reply, which needs the user to speak
        first. Everything written after this, until begin(), is ignored.
        """
        with self._lock:
            self._discard = True
            stats, self._reply = self._reply, None
            if stats is not None:
                self._kill_locked()
                self._failures = 0
                self._start_locked()
        if stats is not None:
            print(stats.summary(cancelled=True), flush=True)
