"""Quadrature rotary encoder with push switch.

Written to serve two different physical parts without code changes, because
the bench encoder is not the shipping one:

    bench    KY-040 module, onboard 10k pull-ups to its + pin
    HAT      bare ALPS EC11E18244AU, 1k pull-ups on the PCB

Both already have external pull-ups, so `pull_up` defaults to False — the
Pi's internal pull-ups stay off rather than paralleling them.

HOW A CLICK IS DETECTED

A detented encoder rests at a fixed electrical state between clicks (on the
bench KY-040, CLK=1 DT=1). One click walks through the other states and
arrives back at a rest state. So a click is counted only on ARRIVAL at a rest
state, using the net direction accumulated since the last rest:

    clean click:    3 -> 1 -> 0 -> 2 -> 3     net -4  -> one step down
    bouncy click:   3 -> 1 -> 3 -> 1 -> 0 -> 2 -> 3
                    net still -4               -> still exactly one step

Contact bounce between two adjacent states adds +1 then -1, which cancels in
the accumulator instead of moving the output. That is the whole fix for the
"50 -> 45 -> 49 -> 40" jitter seen on the first bench run, where every edge
was emitted directly and every bounce became a volume step.

`min_edges` is how much net movement a rest arrival needs to count. 2 rather
than 4 so a fast turn that skips a state (logged as invalid) still registers.

Rest states are a property of the part — full-step detents rest at one state,
half-step detents alternate between two. Default is whatever state the
encoder is sitting in at startup; override with ENC_REST_STATES=0,3 for a
half-step part. tests/encoder_calibrate.py prints the actual path per click
so this is measured, not guessed.

CALLBACKS MUST BE FAST

on_rotate runs on the GPIO callback thread. While it runs, further edges are
not read at the moment they happen; when the thread gets to them it reads
the CURRENT pin state and the intermediate states are lost. Measured on this
Pi: a callback that called amixer directly blocked for 19.6 ms per click and
drove invalid transitions from 0% to 14.8%. Hand anything slow to another
thread — volume.AsyncControl exists for exactly this.
"""
import os
import threading

from gpiozero import Button, DigitalInputDevice

# state = (CLK << 1) | DT
_TRANSITIONS = {
    (0, 1): +1, (1, 3): +1, (3, 2): +1, (2, 0): +1,
    (0, 2): -1, (2, 3): -1, (3, 1): -1, (1, 0): -1,
}


def _env_bool(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).lower() not in ("0", "false", "")


def _env_states(name: str) -> set[int] | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    return {int(s) for s in raw.split(",") if s.strip()}


DEFAULT_CLK = int(os.environ.get("ENC_CLK_PIN", "5"))
DEFAULT_DT = int(os.environ.get("ENC_DT_PIN", "6"))
DEFAULT_SW = int(os.environ.get("ENC_SW_PIN", "13"))
DEFAULT_MIN_EDGES = int(os.environ.get("ENC_MIN_EDGES", "2"))
# Bench KY-040 measured inverted: physical clockwise decodes as negative with
# CLK on GPIO5 and DT on GPIO6. Direction convention is a property of the
# part and its wiring, so re-check this on the ALPS rather than assuming.
DEFAULT_INVERT = _env_bool("ENC_INVERT", "1")
DEFAULT_REST_STATES = _env_states("ENC_REST_STATES")

# Matches the project's existing debounce (>=5ms per CLAUDE.md).
SWITCH_BOUNCE_S = 0.005


class RotaryEncoder:
    """Reports clicks (+1 clockwise / -1 counter-clockwise) and presses."""

    def __init__(
        self,
        clk_pin: int = DEFAULT_CLK,
        dt_pin: int = DEFAULT_DT,
        sw_pin: int | None = DEFAULT_SW,
        pull_up: bool = False,
        invert: bool = DEFAULT_INVERT,
        min_edges: int = DEFAULT_MIN_EDGES,
        rest_states: set[int] | None = DEFAULT_REST_STATES,
        on_rotate=None,
        on_press=None,
        trace: bool = False,
    ):
        self.invert = invert
        self.min_edges = max(1, min_edges)
        self.trace = trace
        self._on_rotate = on_rotate
        self._on_press = on_press

        self.position = 0        # net clicks
        self.raw_edges = 0       # valid state transitions
        self.invalid = 0         # skipped states: bounce or missed edges
        self.cancelled = 0       # rest arrivals with too little net movement
        self.presses = 0

        self._acc = 0
        self._path: list[int] = []
        self._lock = threading.Lock()

        self.clk = DigitalInputDevice(clk_pin, pull_up=pull_up)
        self.dt = DigitalInputDevice(dt_pin, pull_up=pull_up)
        self._state = self._read_state()
        self.rest_states = set(rest_states) if rest_states else {self._state}
        self._path = [self._state]

        for dev in (self.clk, self.dt):
            dev.when_activated = self._on_edge
            dev.when_deactivated = self._on_edge

        self.sw = None
        if sw_pin is not None:
            # Always the Pi's pull-up for the switch: KY-040 clones are
            # inconsistent about populating one, and doubling up is harmless.
            self.sw = Button(sw_pin, pull_up=True, bounce_time=SWITCH_BOUNCE_S)
            self.sw.when_pressed = self._on_switch

    def _read_state(self) -> int:
        return (int(self.clk.value) << 1) | int(self.dt.value)

    def _on_edge(self, _device=None) -> None:
        click = 0
        path_done = None
        with self._lock:
            new_state = self._read_state()
            if new_state == self._state:
                return
            direction = _TRANSITIONS.get((self._state, new_state))
            self._state = new_state
            self._path.append(new_state)

            if direction is None:
                self.invalid += 1
            else:
                self.raw_edges += 1
                self._acc += direction

            if new_state not in self.rest_states:
                return

            # Arrived at a detent. Decide whether a click happened.
            if abs(self._acc) >= self.min_edges:
                click = 1 if self._acc > 0 else -1
                if self.invert:
                    click = -click
                self.position += click
            elif self._acc != 0 or len(self._path) > 1:
                self.cancelled += 1
            path_done, net = self._path, self._acc
            self._acc = 0
            self._path = [new_state]

        if self.trace and path_done is not None and len(path_done) > 1:
            arrow = " -> ".join(str(s) for s in path_done)
            verdict = {1: "CLICK CW", -1: "CLICK CCW", 0: "ignored (bounce)"}[click]
            print(f"  {arrow:<34} net {net:+d}  {verdict}", flush=True)

        # Outside the lock, and must be fast — see module docstring.
        if click and self._on_rotate:
            self._on_rotate(click)

    def _on_switch(self) -> None:
        self.presses += 1
        if self._on_press:
            self._on_press()

    @property
    def error_rate(self) -> float:
        total = self.raw_edges + self.invalid
        return (self.invalid / total * 100) if total else 0.0

    def close(self) -> None:
        for dev in (self.clk, self.dt, self.sw):
            if dev is not None:
                try:
                    dev.close()
                except Exception:
                    pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
