"""AMP_EN (GPIO26) control for the MAX98357A amplifiers.

Why this exists now and did not before: the project used to run the
`googlevoicehat-soundcard` overlay, which drove its own amp-enable line
(GPIO16) as a side effect of playing audio. Nothing in this codebase had to
think about it. Moving to `hifiberry-dac` — required because that overlay's
GPIO16 claim conflicts with the HAT's manual AMP_EN on GPIO26 — means the
overlay now emits I2S and nothing else. Enabling the amplifier became
software's job.

On the HAT, SD_MODE is also the channel selector: U1 (left) takes AMP_EN
directly, U2 (right) through 210k. So this one line does double duty —
driving it high enables both amps AND selects their channels; driving it low
shuts both down.

Kept deliberately tolerant. A bench rig with SD tied straight to VIN is a
reasonable way to work, and on that rig GPIO26 does nothing. The assistant
should still run. So a pin that cannot be claimed is a warning, never a
crash: failing to speak is a far worse outcome than failing to toggle an
enable line that may not be connected to anything.
"""
import os
import threading
import time

# Set AMP_EN_PIN=none to disable entirely — correct for a rig where SD is
# hard-wired high rather than driven.
_PIN_SETTING = os.environ.get("AMP_EN_PIN", "26").strip().lower()

# Class-D amplifiers need a moment to leave shutdown and settle. Audio pushed
# the instant the enable line rises can lose its first fraction of a second,
# which on a short spoken reply is the difference between "hello" and "ello".
# This is a conservative practical value, NOT a figure quoted from the
# datasheet — if speech still gets clipped at the start, raise it and record
# the working value.
SETTLE_S = float(os.environ.get("AMP_SETTLE_S", "0.05"))

_lock = threading.Lock()
_device = None
_unavailable = False


def _get_device():
    """Lazily claim GPIO26. Returns None if unavailable or disabled."""
    global _device, _unavailable

    if _unavailable or _PIN_SETTING in ("none", "off", ""):
        return None
    if _device is not None:
        return _device

    with _lock:
        if _device is not None:
            return _device
        try:
            from gpiozero import DigitalOutputDevice
            _device = DigitalOutputDevice(int(_PIN_SETTING), initial_value=False)
        except Exception as e:
            _unavailable = True
            print(f"⚠️  AMP_EN on GPIO{_PIN_SETTING} unavailable "
                  f"({type(e).__name__}: {e}).")
            print("    Audio will only be heard if SD is wired high another "
                  "way. Set AMP_EN_PIN=none to silence this warning.")
            return None
    return _device


def enable() -> None:
    """Bring the amplifier(s) out of shutdown and wait for them to settle."""
    dev = _get_device()
    if dev is None:
        return
    dev.on()
    time.sleep(SETTLE_S)


def disable() -> None:
    """Return the amplifier(s) to shutdown.

    Worth doing rather than leaving it high: an enabled class-D amp with no
    stream sits amplifying its own noise floor into the speaker, audible as
    hiss in a quiet room.
    """
    dev = _get_device()
    if dev is None:
        return
    dev.off()


class amplifier:
    """Context manager: enable for the duration of playback, then shut down.

    Always disables on the way out, including on exception, so a failure
    mid-playback cannot leave the amp powered and hissing.
    """

    def __enter__(self):
        enable()
        return self

    def __exit__(self, *exc):
        disable()
        return False
