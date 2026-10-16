"""Bench test: rotary encoder driving playback volume, with live audio.

Integration test rather than a subsystem one — encoder, ALSA mixer and
amplifier together. Runs a continuous tone so volume changes are heard as
they happen, which is the only way to tell a working volume control from one
that merely prints plausible numbers.

Turn the knob to change volume, push it to mute. Ctrl+C to stop.

Two things this is really checking:

  direction   clockwise must raise. If it lowers, CLK and DT are swapped —
              a wiring fix, or set ENC_INVERT=1.
  granularity one detent should be one clearly audible step. Several steps
              per click means edges_per_detent is too low for this part; a
              click that does nothing means it is too high.

Both are properties of the physical encoder, so the numbers found here are
for the KY-040 and do NOT carry over to the ALPS EC11 on the HAT.

Usage:
    .venv/bin/python3 tests/encoder_volume_test.py
"""
import pathlib
import signal
import subprocess
import sys
import threading
import time
import wave

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "software"))

from common import amp_enable, audio_devices, encoder, volume  # noqa: E402

SCRATCH = pathlib.Path(__file__).resolve().parent.parent / "scratch"
TONE_PATH = SCRATCH / "volume_test_tone.wav"

RATE = 48000
TONE_HZ = 440
TONE_SECONDS = 10.0
# Well below full scale: the point is to hear volume change, and a tone at
# full scale leaves no headroom to hear the top of the range.
AMPLITUDE = 0.2

_stop = threading.Event()


def make_tone() -> None:
    n = int(RATE * TONE_SECONDS)
    t = np.arange(n) / RATE
    data = np.sin(2 * np.pi * TONE_HZ * t) * AMPLITUDE

    # Fade the loop boundary so the restart is not an audible click that
    # could be mistaken for a fault.
    fade = int(RATE * 0.01)
    ramp = (1 - np.cos(np.linspace(0, np.pi, fade))) / 2
    data[:fade] *= ramp
    data[-fade:] *= ramp[::-1]

    stereo = np.repeat((data * 32767).astype("<i2")[:, None], 2, axis=1)
    SCRATCH.mkdir(exist_ok=True)
    with wave.open(str(TONE_PATH), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(stereo.tobytes())


def tone_loop(device: str) -> None:
    """Keep the tone playing until stopped, restarting when it ends."""
    while not _stop.is_set():
        proc = subprocess.Popen(
            ["aplay", "-D", device, "-q", str(TONE_PATH)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        while proc.poll() is None:
            if _stop.is_set():
                proc.terminate()
                break
            time.sleep(0.1)


def bar(percent: int, width: int = 30) -> str:
    filled = int(round(percent / 100 * width))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def main() -> int:
    print("=" * 62)
    print("ENCODER VOLUME TEST  —  turn to adjust, push to mute")
    print("=" * 62)

    try:
        amp_card = audio_devices.find_card_index(volume.AMP_NAME_HINT, "playback")
        # plughw rather than hw: the tone is S16_LE and the card may want a
        # different format. This test is about volume, not format handling.
        amp_device = f"plughw:{amp_card},0"
    except Exception as e:
        print(f"  ! could not resolve the amp: {e}")
        return 1

    print(f"  amp card        : {amp_card} ({volume.AMP_NAME_HINT}) -> {amp_device}")
    print(f"  volume ceiling  : raw {volume.DEFAULT_MAX}/255  (~0 dB; above "
          f"this the driver boosts and clips)")
    print(f"  step per detent : {volume.STEP} raw (~{volume.STEP * 0.27:.1f} dB)")
    print(f"  click detection : rest-state, min {encoder.DEFAULT_MIN_EDGES} net edges")
    print(f"  direction       : {'inverted (bench KY-040 default)' if encoder.DEFAULT_INVERT else 'normal'}")
    print()

    try:
        start = volume.get_raw()
        print(f"  starting {volume.describe()}")
    except Exception as e:
        print(f"  ! mixer not reachable: {e}")
        return 1

    # Start at a sane level rather than wherever it was left, so the test is
    # repeatable and nobody gets a full-volume surprise.
    volume.set_raw(int(volume.DEFAULT_MAX * 0.5))
    make_tone()

    def show() -> None:
        pct = 0 if volume.is_muted() else volume.get_percent()
        tag = " MUTED" if volume.is_muted() else "      "
        print(f"\r  {bar(pct)} {pct:3d}%{tag}", end="", flush=True)

    # The encoder callbacks only hand work to this thread. Calling amixer
    # directly from them blocked edge reading for ~20 ms per click (measured)
    # and caused both the invalid transitions and the backwards jumps.
    control = volume.AsyncControl(on_change=show)

    try:
        enc = encoder.RotaryEncoder(on_rotate=control.nudge,
                                    on_press=control.toggle_mute)
    except Exception as e:
        print(f"  ! could not open encoder GPIOs: {type(e).__name__}: {e}")
        print("    Stop any running voice assistant first.")
        volume.restore_raw(start)
        return 1

    print(f"  encoder         : CLK=GPIO{encoder.DEFAULT_CLK} "
          f"DT=GPIO{encoder.DEFAULT_DT} SW=GPIO{encoder.DEFAULT_SW}")
    print()
    print("  Turn the knob. Clockwise should get LOUDER.")
    print("  Push to mute/unmute. Ctrl+C when done.")
    print()

    amp_enable.enable()
    player = threading.Thread(target=tone_loop, args=(amp_device,), daemon=True)
    player.start()
    show()

    def finish(_sig=None, _frame=None):
        _stop.set()
        print("\n")
        print("=" * 62)
        print(f"  detents turned : {enc.position:+d}")
        print(f"  raw edges      : {enc.raw_edges}")
        print(f"  invalid        : {enc.invalid} ({enc.error_rate:.1f}%)")
        print(f"  bounce ignored : {enc.cancelled}")
        print(f"  pushes         : {enc.presses}")
        print(f"  final          : {volume.describe()}")
        print("=" * 62)
        volume.restore_raw(start)    # exact, bypasses the clamp
        amp_enable.disable()
        enc.close()
        control.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, finish)
    signal.pause()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
