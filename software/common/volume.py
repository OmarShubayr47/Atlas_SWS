"""Playback volume via the ALSA 'Master' control on the amp card.

The MAX98357A has no volume control of its own — gain is set once by a
resistor strap and that is it. Volume therefore has to happen before audio
reaches the amplifier. The hifiberry-dac driver exposes a software 'Master'
control for exactly this, and using it beats scaling samples in Python for
three reasons: it applies to every playback path rather than only ours, it
costs no per-sample CPU, and `amixer` can inspect and change it
independently when something looks wrong.

This still satisfies the project rule that mute is software and that nothing
touches SD_MODE — the scaling simply lives in the driver instead of in this
codebase.

Measured on this Pi (not assumed):

    Limits: 0 - 255      dBscale-min=-50.00dB, step=0.27dB

So the raw range spans roughly -50 dB to +19 dB, and 0 dB sits near raw 185.
Anything above that is digital boost, which clips on loud passages rather
than getting louder. DEFAULT_MAX caps the usable range there; raise it only
deliberately, and expect distortion if you do.

The card is resolved by NAME on every call rather than cached, because ALSA
card indices genuinely move: this project has already seen the amp appear as
card 0 and later as card 1 across reboots.
"""
import os
import subprocess
import threading

from . import audio_devices

AMP_NAME_HINT = os.environ.get("AMP_NAME_HINT", "hifiberry")
CONTROL = os.environ.get("VOLUME_CONTROL", "Master")

RAW_MIN = 0
RAW_HARD_MAX = 255

# ~0 dB. Above this the driver is boosting, not amplifying.
DEFAULT_MAX = int(os.environ.get("VOLUME_MAX", "185"))

# 0.27 dB per raw step, so 8 raw steps is ~2.2 dB — clearly audible per
# detent without being coarse. The control is already dB-scaled, so linear
# raw steps give perceptually even steps.
STEP = int(os.environ.get("VOLUME_STEP", "8"))

_muted_from: int | None = None


class VolumeError(RuntimeError):
    pass


def _card() -> int:
    return audio_devices.find_card_index(AMP_NAME_HINT, "playback")


def _amixer(*args: str) -> str:
    cmd = ["amixer", "-c", str(_card()), *args]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise VolumeError(f"amixer failed: {r.stderr.strip()[:200]}")
    return r.stdout


def get_raw() -> int:
    """Current volume as a raw 0-255 value."""
    out = _amixer("sget", CONTROL)
    for line in out.splitlines():
        stripped = line.strip()
        # e.g. "Front Left: 223 [87%] [10.21dB]"
        if ":" in stripped and "[" in stripped and "Playback" not in stripped:
            try:
                return int(stripped.split(":")[1].split()[0])
            except (IndexError, ValueError):
                continue
    raise VolumeError(f"could not parse '{CONTROL}' level from amixer output")


def set_raw(value: int) -> int:
    """Set volume, clamped to the safe range. Returns what was actually set."""
    clamped = max(RAW_MIN, min(DEFAULT_MAX, int(value)))
    _amixer("sset", CONTROL, str(clamped))
    return clamped


def get_percent() -> int:
    """Volume as 0-100 across the SAFE range, not the raw range.

    Deliberately not the raw percentage: reporting 87% while the control is
    boosting +10 dB is misleading. Here 100% means the loudest setting that
    is not clipping.
    """
    return round(get_raw() / DEFAULT_MAX * 100)


def restore_raw(value: int) -> int:
    """Set an exact raw value, bypassing the safe-range clamp.

    For putting back a level we previously read, and nothing else. It has to
    skip the clamp: a first version routed restores through set_raw(), so a
    system left at raw 223 (+10 dB boost) was silently "restored" to 185 —
    quietly making the user's assistant ~10 dB quieter while claiming to leave
    things as it found them. Found by testing, not by reading.
    """
    value = max(RAW_MIN, min(RAW_HARD_MAX, int(value)))
    _amixer("sset", CONTROL, str(value))
    return value


def step(detents: int) -> int:
    """Move volume by `detents` steps. Returns the new percentage.

    Unmutes on any change: turning the knob while muted should restore
    sound, which is what every physical volume control does. Crucially it
    steps from the REMEMBERED level, not from the muted zero — a first
    version stepped from 0, so muting at 120 and turning up one click landed
    on 8, near-silent. That reads as "the knob is broken".
    """
    global _muted_from
    if _muted_from is not None:
        base = _muted_from
        _muted_from = None
    else:
        base = get_raw()
    set_raw(base + detents * STEP)
    return get_percent()


def is_muted() -> bool:
    return _muted_from is not None


def toggle_mute() -> bool:
    """Mute or restore. Returns True if now muted.

    The control reports `mute=0`, meaning it has no hardware mute switch, so
    mute is "set to zero and remember where we were". Restoring a remembered
    level rather than a fixed default avoids the unpleasant surprise of
    unmuting straight into full volume.
    """
    global _muted_from
    if _muted_from is None:
        _muted_from = get_raw()
        set_raw(RAW_MIN)
        return True
    set_raw(_muted_from)
    _muted_from = None
    return False


class AsyncControl:
    """Applies knob input on its own thread, so the GPIO thread never waits.

    Each volume change costs ~20 ms of amixer subprocesses (measured). Doing
    that inside the encoder callback blocked edge reading and pushed invalid
    transitions from 0% to 14.8%. Here the callback only adds to a counter —
    microseconds — and this thread drains it.

    Clicks that arrive while a change is being applied are coalesced: five
    fast clicks become one amixer call for five steps, rather than five
    queued calls that lag behind the knob.
    """

    def __init__(self, on_change=None):
        self._pending = 0
        self._mute_toggles = 0
        self._cv = threading.Condition()
        self._closed = False
        self._on_change = on_change
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def nudge(self, clicks: int) -> None:
        with self._cv:
            self._pending += clicks
            self._cv.notify()

    def toggle_mute(self) -> None:
        with self._cv:
            self._mute_toggles += 1
            self._cv.notify()

    def _run(self) -> None:
        while True:
            with self._cv:
                while not (self._pending or self._mute_toggles or self._closed):
                    self._cv.wait()
                if self._closed:
                    return
                clicks, self._pending = self._pending, 0
                toggles, self._mute_toggles = self._mute_toggles, 0
            try:
                # Only the parity of mute presses matters once coalesced.
                if toggles % 2:
                    toggle_mute()
                if clicks:
                    step(clicks)
                if self._on_change:
                    self._on_change()
            except Exception as e:  # noqa: BLE001 - must not kill the thread
                print(f"\n⚠️ volume change failed: {e}")

    def close(self) -> None:
        with self._cv:
            self._closed = True
            self._cv.notify()
        self._thread.join(timeout=2)


def describe() -> str:
    """One-line state summary for logs and tests."""
    raw = get_raw()
    pct = round(raw / DEFAULT_MAX * 100)
    tag = "  [MUTED]" if is_muted() else ""
    return f"volume {pct:3d}%  (raw {raw}/{DEFAULT_MAX}){tag}"
