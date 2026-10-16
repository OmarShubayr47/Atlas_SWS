"""AI_LED (GPIO24): the assistant's state, shown on the PTT button's own light.

The projected UI already shows the state, but the projector can be off, out
of focus, or simply not where the user is looking while they press the
button. A light in the button itself answers "did it hear me?" at the point
of contact, which is where that question is asked.

Patterns (a different rhythm per state, never colour — it is one LED):

    idle        off
    listening   on, steady          "talk now"
    thinking    slow blink
    speaking    on, steady
    error       fast blink

Tolerant on purpose, like amp_enable: on the bench nothing may be wired to
GPIO24, and an LED that cannot be claimed must never stop the assistant.
Set AI_LED_PIN=none to disable it entirely.

On the HAT this drives the K6-6271D04's LED through R6, whose 200 ohm value
is still a placeholder (see CLAUDE.md) — verify the LED polarity and the
current with a multimeter before relying on the brightness.
"""
import os
import threading

_PIN_SETTING = os.environ.get("AI_LED_PIN", "24").strip().lower()

# (on seconds, off seconds) for blinking states; None = steady.
_PATTERNS = {
    "idle": "off",
    "listening": "on",
    "thinking": (0.5, 0.5),
    "speaking": "on",
    "error": (0.1, 0.1),
}

_lock = threading.Lock()
_led = None
_unavailable = False
_current = None


def _get_led():
    global _led, _unavailable
    if _unavailable or _PIN_SETTING in ("none", "off", ""):
        return None
    if _led is not None:
        return _led
    with _lock:
        if _led is None and not _unavailable:
            try:
                from gpiozero import LED
                _led = LED(int(_PIN_SETTING), initial_value=False)
            except Exception as e:  # noqa: BLE001 - optional hardware
                _unavailable = True
                print(f"⚠️  AI_LED on GPIO{_PIN_SETTING} unavailable "
                      f"({type(e).__name__}: {e}); continuing without it. "
                      "Set AI_LED_PIN=none to silence this warning.")
        return _led


def show(state: str) -> None:
    """Show an assistant state. Unknown states turn the LED off."""
    global _current
    led = _get_led()
    if led is None or state == _current:
        return
    _current = state
    pattern = _PATTERNS.get(state, "off")
    try:
        if pattern == "on":
            led.on()
        elif pattern == "off":
            led.off()
        else:
            on_s, off_s = pattern
            led.blink(on_time=on_s, off_time=off_s, background=True)
    except Exception as e:  # noqa: BLE001 - a light is not worth a crash
        print(f"⚠️  AI_LED update failed: {type(e).__name__}: {e}")
