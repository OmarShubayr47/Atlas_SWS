"""Bench test: KY-040 rotary encoder — raw edges, direction, push switch.

Subsystem test only. Prints RAW counts and makes no assumption about how
many quadrature edges make one detent: that ratio differs between encoder
parts, and the bench part (KY-040 clone) is NOT the part on the HAT
(ALPS EC11E18244AU). Turn the shaft one full revolution and read the
numbers off, rather than trusting a hard-coded constant.

Wiring (bench):
    CLK -> GPIO5  (pin 29)
    DT  -> GPIO6  (pin 31)
    SW  -> GPIO13 (pin 33)
    +   -> 3.3V   (NOT 5V — the module's onboard pull-ups reference this
                   pin, so it sets the GPIO input high level directly, and
                   Pi 5 GPIOs are not 5V tolerant)
    GND -> GND

No external pull-ups are added for CLK/DT: the module already has 10k to
its + pin, and stacking the HAT's 1k against them would give ~909R and an
unpredictable divider. SW is driven with the internal pull-up enabled,
because whether a given KY-040 clone populates a third resistor for SW is
not consistent across boards.

Decoding is a 2-bit Gray-code state machine rather than "count edges on CLK
and read DT". The state machine rejects impossible transitions, which is
what makes it tolerant of contact bounce; edge-plus-level sampling reads
whatever DT happens to be doing mid-bounce and produces phantom steps.

INVALID transitions are counted and reported. That number is the real
measure of contact quality on this bench part — expect it to be non-zero
on a KY-040 at 10k pull-ups. See CLAUDE.md for why that does not reflect
on the HAT schematic.

Run:
    .venv/bin/python3 tests/encoder_test.py
Ctrl+C to stop and print the summary.
"""
import signal
import sys
import time

from gpiozero import Button, DigitalInputDevice

CLK_PIN = 5
DT_PIN = 6
SW_PIN = 13

# Gray-code transition table. State is (CLK << 1) | DT.
#   clockwise:        00 -> 01 -> 11 -> 10 -> 00   (0,1,3,2)
#   counter-clockwise: 00 -> 10 -> 11 -> 01 -> 00  (0,2,3,1)
# Anything not listed is either no movement (same state) or a skipped
# state, which means an edge was missed or a contact bounced.
_TRANSITIONS = {
    (0, 1): +1, (1, 3): +1, (3, 2): +1, (2, 0): +1,
    (0, 2): -1, (2, 3): -1, (3, 1): -1, (1, 0): -1,
}


class EncoderMonitor:
    def __init__(self):
        # pull_up=None + active_state is not used here: the module supplies
        # its own pull-ups on CLK/DT, so the Pi's internal ones are left off
        # to avoid paralleling them.
        self.clk = DigitalInputDevice(CLK_PIN, pull_up=False)
        self.dt = DigitalInputDevice(DT_PIN, pull_up=False)
        self.sw = Button(SW_PIN, pull_up=True, bounce_time=0.005)

        self.position = 0
        self.raw_edges = 0
        self.invalid = 0
        self.sw_presses = 0
        self.last_direction = 0
        self.started = time.monotonic()

        self._state = self._read_state()

        # Both pins, both edges — a quadrature decoder that watches only one
        # phase throws away half the resolution and all of its error
        # detection.
        for dev in (self.clk, self.dt):
            dev.when_activated = self._on_edge
            dev.when_deactivated = self._on_edge

        self.sw.when_pressed = self._on_press

    def _read_state(self) -> int:
        return (int(self.clk.value) << 1) | int(self.dt.value)

    def _on_edge(self, _device=None) -> None:
        new_state = self._read_state()
        if new_state == self._state:
            return  # same level; a glitch that settled back

        step = _TRANSITIONS.get((self._state, new_state))
        self._state = new_state

        if step is None:
            self.invalid += 1
            print(f"  ?? invalid transition  (bounce or missed edge)   "
                  f"invalid_total={self.invalid}")
            return

        self.raw_edges += 1
        self.position += step
        self.last_direction = step
        arrow = "CW " if step > 0 else "CCW"
        print(f"  {arrow}  raw_edges={self.raw_edges:5d}  "
              f"net_position={self.position:+5d}  invalid={self.invalid}")

    def _on_press(self) -> None:
        self.sw_presses += 1
        print(f"  [SW] push #{self.sw_presses}  "
              f"(this is the mute control on the HAT)")

    def summary(self) -> str:
        elapsed = time.monotonic() - self.started
        total = self.raw_edges + self.invalid
        error_pct = (self.invalid / total * 100) if total else 0.0
        return (
            f"\n{'=' * 58}\n"
            f"SUMMARY after {elapsed:.1f}s\n"
            f"  raw valid edges : {self.raw_edges}\n"
            f"  net position    : {self.position:+d}\n"
            f"  invalid         : {self.invalid}  ({error_pct:.1f}% of transitions)\n"
            f"  SW presses      : {self.sw_presses}\n"
            f"{'=' * 58}\n"
            f"CALIBRATION: divide 'raw valid edges' by the number of full\n"
            f"revolutions you turned to get edges-per-revolution. Divide by\n"
            f"detents-per-revolution (24 on most KY-040 boards, but COUNT\n"
            f"the clicks rather than assuming) to get edges-per-detent.\n"
            f"\n"
            f"This ratio is for the KY-040 ONLY. The HAT uses an ALPS\n"
            f"EC11E18244AU with 1k pull-ups; do not carry this number over.\n"
        )


def main() -> int:
    print("=" * 58)
    print("KY-040 ENCODER BENCH TEST")
    print("=" * 58)
    print(f"  CLK -> GPIO{CLK_PIN}   DT -> GPIO{DT_PIN}   SW -> GPIO{SW_PIN}")
    print("  + must be on 3.3V, not 5V")
    print()
    print("Turn the shaft slowly one way, then the other, then push it.")
    print("Then turn EXACTLY one full revolution for calibration.")
    print("Ctrl+C when done.\n")

    try:
        monitor = EncoderMonitor()
    except Exception as e:
        print(f"Could not open encoder GPIOs: {type(e).__name__}: {e}")
        print("Check nothing else is holding GPIO 5/6/13.")
        return 1

    print(f"initial state: CLK={int(monitor.clk.value)} "
          f"DT={int(monitor.dt.value)}  (both should read 1 at rest,\n"
          f"because the module's pull-ups hold them high)\n")

    def _stop(_sig, _frame):
        print(monitor.summary())
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    signal.pause()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
