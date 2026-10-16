"""Bench test: MAX98357A Amp 1 (left) — AMP_EN control and tone playback.

Tests one amplifier only. Amp 2 is wired for I2S and SD but has no VIN/GND
this session, so it is inert: silence from the right channel is the EXPECTED
result here, not a fault. Stereo separation is not under test.

Wiring (bench):
    BCLK -> GPIO18 (pin 12)     shared
    LRC  -> GPIO19 (pin 35)     shared
    DIN  -> GPIO21 (pin 40)     shared
    SD   -> GPIO26 (pin 37)     Amp1 direct / Amp2 via 210k
    GAIN -> VIN    (6 dB)
    VIN  -> external 5V bench supply, NOT the 40-pin header
    GND  -> common with Pi

Why this script checks the device-tree overlay before doing anything:
`googlevoicehat-soundcard` claims GPIO16 as its own amp-enable line and
never drives GPIO26. With that overlay active the amp stays in shutdown and
produces silence that is indistinguishable from a broken solder joint, a
dead speaker or a wrong pin. Refusing up front turns an hour of wiring
forensics into one line of output.

The channel-select check is the interesting part. On the HAT, SD_MODE is
driven directly from AMP_EN for U1 and through a 210k resistor for U2; the
resulting pin voltage is what selects which channel each amp reproduces.
Playing a LEFT-only tone and then a RIGHT-only tone through a single
powered amp tells you whether that selection actually landed on left, which
a mono tone cannot.

Run:
    .venv/bin/python3 tests/amp_test.py
"""
import pathlib
import re
import subprocess
import sys
import wave

import numpy as np

CONFIG_TXT = pathlib.Path("/boot/firmware/config.txt")
BLOCKING_OVERLAY = "googlevoicehat-soundcard"

AMP_EN_PIN = 26
RATE = 48000
TONE_HZ = 440
TONE_SECONDS = 2.0
# Conservative. The bench speakers are 2-3W and GAIN is at 6 dB; this is a
# "can I hear it" test, not a power test.
AMPLITUDE = 0.25

SCRATCH = pathlib.Path(__file__).resolve().parent.parent / "scratch"

# Tried in order. The card name changes with the overlay, so this cannot be
# a single hard-coded string.
CARD_HINTS = ["hifiberry", "sndrpihifiberry", "MAX98357", "sndrpigooglevoi"]


def check_overlay() -> bool:
    """True if safe to proceed. Prints the reason if not."""
    try:
        text = CONFIG_TXT.read_text()
    except OSError as e:
        print(f"  ! could not read {CONFIG_TXT}: {e}")
        return True  # don't block on a read failure

    active = [
        ln.strip() for ln in text.splitlines()
        if ln.strip().startswith("dtoverlay=") and BLOCKING_OVERLAY in ln
    ]
    if not active:
        print(f"  overlay check: OK, {BLOCKING_OVERLAY} is not active")
        return True

    print()
    print("  " + "!" * 54)
    print(f"  BLOCKED: {BLOCKING_OVERLAY} is still active")
    print("  " + "!" * 54)
    print(f"  found in {CONFIG_TXT}: {active[0]}")
    print()
    print("  That overlay drives GPIO16 as its amp-enable and never touches")
    print("  GPIO26, which is where SD is wired. The amp will stay in")
    print("  shutdown and you will hear nothing, which looks exactly like a")
    print("  wiring fault. Not running the test rather than wasting your")
    print("  time chasing that.")
    print()
    print("  Fix (Option A — validates the HAT design):")
    print(f"    1. comment out  dtoverlay={BLOCKING_OVERLAY}")
    print("    2. add          dtoverlay=hifiberry-dac")
    print("    3. sudo reboot")
    print()
    print("  Playback-only overlay: I2S bench capture stops working. Fine —")
    print("  the final mic is USB.")
    return False


def find_playback_card() -> tuple[int, str] | None:
    """Resolve the amp's ALSA card by name, never by a fixed index."""
    try:
        out = subprocess.run(["aplay", "-l"], capture_output=True,
                             text=True, timeout=10).stdout
    except Exception as e:
        print(f"  ! aplay -l failed: {e}")
        return None

    cards = []
    for line in out.splitlines():
        m = re.match(r"^card (\d+): (\S+) \[([^\]]+)\]", line)
        if m:
            cards.append((int(m.group(1)), m.group(2), m.group(3)))

    for hint in CARD_HINTS:
        for idx, cid, desc in cards:
            if hint.lower() in cid.lower() or hint.lower() in desc.lower():
                return idx, cid

    print("  ! no playback card matched any of:", ", ".join(CARD_HINTS))
    print("    cards present:")
    for idx, cid, desc in cards:
        print(f"      card {idx}: {cid} [{desc}]")
    print("    set the right one with AMP_NAME_HINT, or check the overlay.")
    return None


def make_tone(path: pathlib.Path, left: bool, right: bool) -> None:
    """Write a stereo WAV with the tone on the selected channel(s)."""
    n = int(RATE * TONE_SECONDS)
    t = np.arange(n) / RATE
    wave_data = np.sin(2 * np.pi * TONE_HZ * t) * AMPLITUDE

    # 5ms raised-cosine fades. A tone that starts at full amplitude on the
    # first sample puts a step through the speaker, which sounds like a
    # click and tells you nothing about the amp.
    fade = int(RATE * 0.005)
    if fade * 2 < n:
        ramp = (1 - np.cos(np.linspace(0, np.pi, fade))) / 2
        wave_data[:fade] *= ramp
        wave_data[-fade:] *= ramp[::-1]

    stereo = np.zeros((n, 2), dtype=np.float64)
    if left:
        stereo[:, 0] = wave_data
    if right:
        stereo[:, 1] = wave_data

    pcm = np.clip(stereo * 32767, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(pcm.tobytes())


def step(number: int, title: str, expect: str, auto: bool) -> None:
    """Announce a step and wait, so results can't be misattributed.

    Four two-second tones back to back take eight seconds total, which is
    not enough time to register what you heard. Gating each step on a
    keypress costs nothing and prevents the most likely failure of this
    test: correct audio, wrong notes.
    """
    print()
    print("-" * 58)
    print(f"STEP {number}  {title}")
    print(f"        EXPECT: {expect}")
    print("-" * 58)
    if not auto:
        try:
            input("        press Enter to play...")
        except EOFError:
            pass
    print("        >>> playing <<<")


def play(path: pathlib.Path, card: int) -> bool:
    # plughw, not hw: this is a "does sound come out" test, so let ALSA
    # convert if the card wants a different format. Format-exactness is the
    # application's problem, not this test's.
    cmd = ["aplay", "-D", f"plughw:{card},0", "-q", str(path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    aplay failed: {r.stderr.strip()[:200]}")
        return False
    return True


def main() -> int:
    auto = "--auto" in sys.argv
    print("=" * 58)
    print("MAX98357A AMP 1 (LEFT) BENCH TEST")
    print("=" * 58)
    print("  Amp 2 has no VIN/GND this session — it is inert.")
    print("  Silence from the right channel is EXPECTED, not a fault.\n")

    if not check_overlay():
        return 2

    found = find_playback_card()
    if not found:
        return 1
    card, card_id = found
    print(f"  playback card : {card} ({card_id})")

    SCRATCH.mkdir(exist_ok=True)

    try:
        from gpiozero import DigitalOutputDevice
        amp_en = DigitalOutputDevice(AMP_EN_PIN, initial_value=False)
    except Exception as e:
        print(f"  ! could not claim GPIO{AMP_EN_PIN}: {type(e).__name__}: {e}")
        return 1

    left_wav = SCRATCH / "amp_test_left.wav"
    right_wav = SCRATCH / "amp_test_right.wav"
    both_wav = SCRATCH / "amp_test_both.wav"
    make_tone(left_wav, left=True, right=False)
    make_tone(right_wav, left=False, right=True)
    make_tone(both_wav, left=True, right=True)

    try:
        amp_en.off()
        step(1, f"AMP_EN (GPIO{AMP_EN_PIN}) LOW — amp in shutdown",
             "silence. If you hear this tone, SD is not actually on GPIO26.",
             auto)
        play(both_wav, card)

        amp_en.on()
        step(2, "AMP_EN HIGH, LEFT channel only",
             "a clear 440 Hz tone from the Amp 1 speaker.", auto)
        play(left_wav, card)

        step(3, "AMP_EN HIGH, RIGHT channel only",
             "silence — confirms Amp 1 selected LEFT. If you DO hear it, "
             "SD_MODE landed on (L+R)/2, not left.", auto)
        play(right_wav, card)

        step(4, "AMP_EN HIGH, both channels",
             "same loudness as step 2 (only left is wired).", auto)
        play(both_wav, card)

    finally:
        # Leave the amp in shutdown. A powered-up class-D amp with no stream
        # is free to sit there amplifying its own noise floor into a speaker.
        amp_en.off()
        amp_en.close()
        print(f"\n  AMP_EN returned LOW (amp in shutdown)")

    print()
    print("=" * 58)
    print("Report which steps produced sound. The diagnostic pattern:")
    print("  1 silent, 2 loud, 3 silent, 4 loud  -> correct, left selected")
    print("  all silent                          -> amp not enabling; check")
    print("                                         5V supply and SD wire")
    print("  1 loud                              -> SD not on GPIO26")
    print("  2 and 3 both loud                   -> mono mode, not left")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
