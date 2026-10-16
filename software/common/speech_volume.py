"""Speech volume and mute for the assistant's voice, applied in software.

WHY NOT THE ALSA MIXER (common/volume.py)

The assistant normally speaks through the projector over HDMI, using the
PCM "plug:'hdmi:CARD=vc4hdmi0,DEV=0'". On this Pi, ALSA's card definition
(/usr/share/alsa/cards/vc4-hdmi.conf) only puts a volume stage (softvol) in
the card's *default* PCM; the `hdmi` PCM we use goes straight to the
hardware. So the HDMI card's "PCM" control, and the hifiberry "Master"
control that volume.py drives, both leave the projector's sound unchanged.
Scaling the samples ourselves, just before they are written, works on
whichever output is active — HDMI or the I2S amp.

It also makes mute real. The mixer controls on this Pi report mute=0 (no
mute switch), and their lowest step is about -50 dB, not silence (status
doc, open item 7). Here mute writes zeros.

LEVELS

The level is an attenuation in dB below the loudest setting, in steps of
STEP_DB per encoder click. 0 dB is the loudest and equals today's verified
comfortable setting (SPEECH_GAIN_DB on the HDMI path), so the knob can only
ever make speech quieter than what was tested, never push it into clipping.
The bottom step is treated as silent, like any physical volume knob at 0.

The level (not the mute) is saved to a small JSON file so a reboot does not
jump back to full volume. Mute is deliberately not saved: an assistant that
comes back from a reboot silent, for no visible reason, looks broken.
"""
import json
import os
import pathlib
import threading
import time
from datetime import datetime

from . import ui_events

STEP_DB = float(os.environ.get("VOLUME_STEP_DB", "2"))
MIN_DB = float(os.environ.get("VOLUME_MIN_DB", "-40"))
STATE_PATH = pathlib.Path(
    os.environ.get("VOLUME_STATE_PATH", "~/.local/state/sws/volume.json")
).expanduser()
# Coalesce saves: a fast turn of the knob is one write, not twenty.
SAVE_DELAY_S = 2.0


class SpeechVolume:
    def __init__(self, state_path: pathlib.Path = STATE_PATH,
                 step_db: float = STEP_DB, min_db: float = MIN_DB):
        self.step_db = abs(step_db) or 2.0
        self.min_db = -abs(min_db) or -40.0
        self._path = pathlib.Path(state_path)
        self._lock = threading.Lock()
        self._level_db = 0.0
        self._muted = False
        self._dirty = threading.Event()
        self._load()
        threading.Thread(target=self._saver, daemon=True,
                         name="volume-saver").start()

    # --- state --------------------------------------------------------
    def _clamp(self, level: float) -> float:
        return max(self.min_db, min(0.0, level))

    def level_db(self) -> float:
        with self._lock:
            return self._level_db

    def muted(self) -> bool:
        with self._lock:
            return self._muted

    def silent(self) -> bool:
        """True when speech should not be heard at all (muted or at 0%)."""
        with self._lock:
            return self._muted or self._level_db <= self.min_db

    def gain_db(self) -> float | None:
        """Attenuation to apply now, in dB; None means write silence."""
        with self._lock:
            if self._muted or self._level_db <= self.min_db:
                return None
            return self._level_db

    def percent(self) -> int:
        with self._lock:
            level = self._level_db
        return round(100 * (level - self.min_db) / -self.min_db)

    # --- controls (called from the encoder's GPIO thread: keep fast) ----
    def step(self, clicks: int) -> None:
        """Turn the knob by `clicks` detents (+ louder, - quieter).

        Turning while muted unmutes from the remembered level, the way every
        physical volume knob behaves — the same rule volume.py follows.
        """
        with self._lock:
            self._muted = False
            self._level_db = self._clamp(self._level_db + clicks * self.step_db)
        self._dirty.set()
        self.publish()

    def toggle_mute(self) -> bool:
        """Mute or unmute. Returns True if now muted."""
        with self._lock:
            self._muted = not self._muted
            muted = self._muted
        self.publish()
        return muted

    def publish(self) -> None:
        """Tell the projected UI (non-blocking; fine on the GPIO thread)."""
        with self._lock:
            muted, level = self._muted, self._level_db
        ui_events.publish("volume", percent=self.percent(), muted=muted,
                          db=round(level, 1))

    def describe(self) -> str:
        with self._lock:
            muted, level = self._muted, self._level_db
        tag = "  [MUTED]" if muted else ""
        return f"speech volume {self.percent()}% ({level:+.0f} dB){tag}"

    # --- persistence ------------------------------------------------------
    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text())
            self._level_db = self._clamp(float(data["level_db"]))
        except FileNotFoundError:
            pass
        except (OSError, ValueError, KeyError, TypeError) as e:
            print(f"⚠️  Ignoring unreadable volume state {self._path}: {e}")

    def _saver(self) -> None:
        while True:
            self._dirty.wait()
            time.sleep(SAVE_DELAY_S)
            self._dirty.clear()
            self._save()

    def _save(self) -> None:
        with self._lock:
            level = self._level_db
        payload = {"level_db": level,
                   "saved": datetime.now().astimezone().isoformat(timespec="seconds")}
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload) + "\n")
            # Atomic replace: a power cut mid-write leaves the old file, not
            # a half-written one.
            os.replace(tmp, self._path)
        except OSError as e:
            print(f"⚠️  Could not save volume state: {e}")
