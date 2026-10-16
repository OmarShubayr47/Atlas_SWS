"""Bench test: both MAX98357A amps as a stereo pair — channel select via SD_MODE.

This is the test that validates the HAT's channel-select design:

    AMP_EN (GPIO26) ─┬───────────── U1 SD_MODE   (direct       -> LEFT)
                     └── 210 kΩ ─── U2 SD_MODE   (via divider  -> RIGHT)

Each MAX98357A decides what to reproduce from the voltage on its SD_MODE pin:
shutdown, left, right, or mono (L+R)/2. U2's 210 kΩ works against the chip's
internal SD_MODE pull-down to pull its pin into the "right" band while U1,
driven directly, sits in the "left" band. Whether that actually happened is
exactly what a left-only tone and a right-only tone reveal — a mono tone
cannot tell the modes apart.

After every tone the script asks which speaker you heard, then infers each
amp's mode from the pattern rather than you having to decode it.

Before starting: label the speakers physically. "Left" means the one on U1
(SD direct), "right" the one on U2 (SD via 210 kΩ).

Usage:
    python tests/stereo_test.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "software"))

import amp_test  # noqa: E402  (reuses overlay check, card lookup, tone, play)
from common import volume  # noqa: E402

HEARD = {"l": "left", "r": "right", "b": "both", "n": "none"}


def ask(prompt: str) -> str:
    while True:
        try:
            a = input(f"        {prompt} [l]eft / [r]ight / [b]oth / [n]one: ").strip().lower()
        except EOFError:
            return "none"
        if a[:1] in HEARD:
            return HEARD[a[:1]]


def mode_of(heard_on_left_tone: bool, heard_on_right_tone: bool) -> str:
    return {
        (True, False): "LEFT",
        (False, True): "RIGHT",
        (True, True): "MONO (L+R)/2",
        (False, False): "SHUTDOWN / silent",
    }[(heard_on_left_tone, heard_on_right_tone)]


def main() -> int:
    print("=" * 62)
    print("STEREO TEST — MAX98357A x2, channel select via SD_MODE")
    print("=" * 62)
    print("  U1 = LEFT speaker (SD direct)   U2 = RIGHT speaker (SD via 210k)")
    print()

    if not amp_test.check_overlay():
        return 2
    found = amp_test.find_playback_card()
    if not found:
        return 1
    card, card_id = found
    print(f"  playback card : {card} ({card_id})")

    from gpiozero import DigitalOutputDevice
    try:
        amp_en = DigitalOutputDevice(amp_test.AMP_EN_PIN, initial_value=False)
    except Exception as e:
        print(f"  ! could not claim GPIO{amp_test.AMP_EN_PIN}: {e}")
        return 1

    # Sane, repeatable level; restored exactly at the end.
    start_vol = volume.get_raw()
    volume.set_raw(int(volume.DEFAULT_MAX * 0.6))

    sc = amp_test.SCRATCH
    sc.mkdir(exist_ok=True)
    left, right, both = sc / "st_left.wav", sc / "st_right.wav", sc / "st_both.wav"
    amp_test.make_tone(left, left=True, right=False)
    amp_test.make_tone(right, left=False, right=True)
    amp_test.make_tone(both, left=True, right=True)

    sd = {}
    r = {}
    try:
        # --- measurement first: the voltage IS the channel selection ---
        amp_en.on()
        print()
        print("-" * 62)
        print("MEASURE  AMP_EN is now HIGH, no audio playing.")
        print("         Multimeter, black on GND, red on each amp's SD pin.")
        print("-" * 62)
        for amp in ("U1 (left, direct)", "U2 (right, 210k)"):
            try:
                sd[amp] = input(f"        {amp} SD voltage in volts (Enter to skip): ").strip()
            except EOFError:
                sd[amp] = ""

        amp_en.off()
        amp_test.step(1, "AMP_EN LOW — both amps should be in shutdown",
                      "NO sound from either speaker.", auto=False)
        amp_test.play(both, card)
        r[1] = ask("heard?")

        amp_en.on()
        amp_test.step(2, "AMP_EN HIGH — LEFT-only tone",
                      "LEFT speaker only.", auto=False)
        amp_test.play(left, card)
        r[2] = ask("heard?")

        amp_test.step(3, "AMP_EN HIGH — RIGHT-only tone",
                      "RIGHT speaker only.", auto=False)
        amp_test.play(right, card)
        r[3] = ask("heard?")

        amp_test.step(4, "AMP_EN HIGH — both channels",
                      "BOTH speakers, similar loudness.", auto=False)
        amp_test.play(both, card)
        r[4] = ask("heard?")
    finally:
        amp_en.off()
        amp_en.close()
        volume.restore_raw(start_vol)

    def on(res: str, side: str) -> bool:
        return res in (side, "both")

    u1 = mode_of(on(r[2], "left"), on(r[3], "left"))
    u2 = mode_of(on(r[2], "right"), on(r[3], "right"))

    print()
    print("=" * 62)
    print("RESULTS")
    for amp, v in sd.items():
        print(f"  SD voltage {amp:<18}: {v + ' V' if v else '(not measured)'}")
    print(f"  heard: 1={r[1]}  2(L tone)={r[2]}  3(R tone)={r[3]}  4(both)={r[4]}")
    print()
    print(f"  U1 (left)  inferred mode : {u1:<20} {'OK' if u1 == 'LEFT' else '<-- expected LEFT'}")
    print(f"  U2 (right) inferred mode : {u2:<20} {'OK' if u2 == 'RIGHT' else '<-- expected RIGHT'}")
    print()

    problems = []
    if r[1] != "none":
        problems.append(f"Step 1: {r[1]} sounded with AMP_EN LOW — that amp's SD is "
                        "not controlled by GPIO26 (floating high, or wired elsewhere).")
    if u2 == "MONO (L+R)/2":
        problems.append("U2 is in MONO: its SD_MODE voltage landed in the mono band, "
                        "not the right band. Compare the measured U2 SD voltage with "
                        "the datasheet's SD_MODE threshold table — the 210k value or "
                        "its solder joints are the suspect.")
    if u2 == "SHUTDOWN / silent":
        problems.append("U2 silent: its SD voltage is too low to enable it, or it has "
                        "no power/speaker. Check VIN/GND, the speaker joints, and "
                        "whether the 210k is open.")
    if u2 == "LEFT":
        problems.append("U2 behaves like U1: the 210k divider is not in effect "
                        "(shorted, bypassed, or SD wired direct).")
    if u1 == "RIGHT" and u2 == "LEFT":
        problems = ["Channels SWAPPED: speakers or amps are on the wrong sides."]
    if u1 in ("MONO (L+R)/2", "SHUTDOWN / silent"):
        problems.append(f"U1 is {u1}: with SD driven directly it should be LEFT. "
                        "Check U1's SD joint and that GPIO26 really reaches it.")

    if not problems and u1 == "LEFT" and u2 == "RIGHT" and r[4] == "both":
        print("  PASS — true stereo. The HAT channel-select design works on the bench.")
    else:
        for p in problems or ["Unexpected pattern — paste this output."]:
            print(f"  ! {p}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
