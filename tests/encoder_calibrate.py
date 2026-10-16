"""Measure how this encoder actually moves through its states per click.

No audio, no volume — just the path each click takes, so the settings in
common/encoder.py are set from a measurement rather than a guess:

    3 -> 1 -> 0 -> 2 -> 3     net -4  CLICK CW
      full-step part: rests only at one state, four edges per click

    3 -> 1 -> 0               net -2  CLICK CW
    0 -> 2 -> 3               net -2  CLICK CW
      half-step part: rests alternately at two states -> ENC_REST_STATES=0,3

Also confirms direction: a physical clockwise turn must print CLICK CW. If it
prints CCW, set ENC_INVERT the other way.

Do exactly this, SLOWLY, feeling each click:
    5 clicks clockwise, pause, 5 clicks counter-clockwise, then Ctrl+C.

Usage:
    .venv/bin/python3 tests/encoder_calibrate.py
"""
import pathlib
import signal
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "software"))

from common import encoder  # noqa: E402


def main() -> int:
    print("=" * 62)
    print("ENCODER CALIBRATION  —  per-click state paths")
    print("=" * 62)
    try:
        enc = encoder.RotaryEncoder(trace=True)
    except Exception as e:
        print(f"  ! could not open encoder GPIOs: {type(e).__name__}: {e}")
        print("    Stop any running voice assistant or volume test first.")
        return 1

    print(f"  rest state(s) : {sorted(enc.rest_states)}  (state = CLK*2 + DT)")
    print(f"  invert        : {enc.invert}")
    print(f"  min net edges : {enc.min_edges}")
    print()
    print("  SLOWLY: 5 clicks CLOCKWISE, pause, 5 clicks COUNTER-clockwise.")
    print("  Ctrl+C when done.\n")

    def finish(_sig=None, _frame=None):
        print()
        print("=" * 62)
        print(f"  net clicks     : {enc.position:+d}   (expect 0 after 5 CW + 5 CCW)")
        print(f"  valid edges    : {enc.raw_edges}")
        print(f"  invalid        : {enc.invalid} ({enc.error_rate:.1f}%)")
        print(f"  bounce ignored : {enc.cancelled}")
        print("=" * 62)
        print("  Paste the whole output — the path lines are the measurement.")
        enc.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, finish)
    signal.pause()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
