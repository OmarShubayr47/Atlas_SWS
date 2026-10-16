"""Bench test: PTT/AI button and restart button.

PRINTS ONLY. This script will NOT reboot the Pi, by design — a test that
reboots the machine destroys the evidence of whether it worked. The restart
handler prints exactly what it would run in production instead.

Wiring (bench): both buttons momentary, one leg to GPIO, other to GND,
using the Pi's internal pull-ups (so idle reads high, pressed reads low).

    PTT / AI button -> GPIO22 (pin 15)
    Restart button  -> GPIO27 (pin 13)

GPIO22 is the same pin the working voice assistant already uses, so a
success here also confirms nothing in the new wiring disturbed it.

--- PRODUCTION NOTE: the restart button needs a sudoers rule ---

`sudo reboot` from a GPIO callback will hang waiting for a password that
nobody can type, even though the same command works when you run it by hand
in a terminal (your shell has a cached sudo timestamp; the callback does
not). Running the whole assistant as root to avoid this is the wrong trade —
it gives every part of the voice pipeline root for the sake of one button.

Add a narrow rule instead:

    sudo visudo -f /etc/sudoers.d/swspi-reboot
    swspi ALL=(root) NOPASSWD: /sbin/reboot

Then verify it non-interactively, which is the case that actually matters:

    sudo -n /sbin/reboot --help    # must NOT prompt

Test from a real button press, never from the shell.

Run:
    .venv/bin/python3 tests/button_test.py
Ctrl+C to stop.
"""
import signal
import subprocess
import sys
import time

from gpiozero import Button

PTT_PIN = 22
RESTART_PIN = 27

# Matches the debounce used elsewhere in the project (>=5ms per CLAUDE.md).
BOUNCE_S = 0.005

# Deliberately long. A restart is destructive and a brush against the panel
# should not trigger it; requiring a sustained hold is the cheapest possible
# confirmation gate for a control with no screen.
RESTART_HOLD_S = 2.0


class ButtonMonitor:
    def __init__(self):
        self.ptt = Button(PTT_PIN, pull_up=True, bounce_time=BOUNCE_S)
        self.restart = Button(RESTART_PIN, pull_up=True, bounce_time=BOUNCE_S,
                              hold_time=RESTART_HOLD_S)

        self.ptt_presses = 0
        self.restart_presses = 0
        self.restart_holds = 0
        self._ptt_down_at = 0.0
        self.started = time.monotonic()

        self.ptt.when_pressed = self._ptt_down
        self.ptt.when_released = self._ptt_up
        self.restart.when_pressed = self._restart_down
        self.restart.when_held = self._restart_held

    def _ptt_down(self) -> None:
        self._ptt_down_at = time.monotonic()
        self.ptt_presses += 1
        print(f"  [PTT] pressed   #{self.ptt_presses}")

    def _ptt_up(self) -> None:
        held = time.monotonic() - self._ptt_down_at
        print(f"  [PTT] released  held {held * 1000:.0f} ms")

    def _restart_down(self) -> None:
        self.restart_presses += 1
        print(f"  [RESTART] pressed #{self.restart_presses} — "
              f"hold {RESTART_HOLD_S:.0f}s to trigger")

    def _restart_held(self) -> None:
        self.restart_holds += 1
        print(f"  [RESTART] HELD {RESTART_HOLD_S:.0f}s — in production this "
              f"would run: sudo reboot")
        print(f"            (test mode: not rebooting)")
        self._report_sudo_readiness()

    @staticmethod
    def _report_sudo_readiness() -> None:
        """Check the non-interactive sudo path without actually rebooting.

        `sudo -n true` fails if a password would be required — which is the
        exact condition that makes the button work by hand and fail from a
        callback.
        """
        try:
            r = subprocess.run(["sudo", "-n", "true"],
                               capture_output=True, timeout=5)
            if r.returncode == 0:
                print("            sudo -n works: reboot would succeed")
            else:
                print("            sudo -n FAILS: reboot would hang on a "
                      "password prompt.")
                print("            Add /etc/sudoers.d/swspi-reboot "
                      "(see this file's docstring).")
        except Exception as e:
            print(f"            could not check sudo: {e}")

    def summary(self) -> str:
        elapsed = time.monotonic() - self.started
        return (
            f"\n{'=' * 58}\n"
            f"SUMMARY after {elapsed:.1f}s\n"
            f"  PTT presses        : {self.ptt_presses}\n"
            f"  Restart presses    : {self.restart_presses}\n"
            f"  Restart holds (>={RESTART_HOLD_S:.0f}s) : {self.restart_holds}\n"
            f"{'=' * 58}\n"
        )


def main() -> int:
    print("=" * 58)
    print("BUTTON BENCH TEST  —  WILL NOT REBOOT")
    print("=" * 58)
    print(f"  PTT / AI  -> GPIO{PTT_PIN} (pin 15)")
    print(f"  Restart   -> GPIO{RESTART_PIN} (pin 13)")
    print()
    print("Press PTT a few times (try short taps and long holds).")
    print(f"Press restart briefly, then hold it {RESTART_HOLD_S:.0f}s.")
    print("Ctrl+C when done.\n")

    try:
        monitor = ButtonMonitor()
    except Exception as e:
        print(f"Could not open button GPIOs: {type(e).__name__}: {e}")
        print("If GPIO22 is busy, stop any running voice assistant first.")
        return 1

    print(f"idle levels: PTT={'HIGH' if not monitor.ptt.is_pressed else 'LOW'}  "
          f"RESTART={'HIGH' if not monitor.restart.is_pressed else 'LOW'}")
    print("(both should read HIGH at rest with internal pull-ups; a pin\n"
          " reading LOW when untouched means it is shorted to ground)\n")

    def _stop(_sig, _frame):
        print(monitor.summary())
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    signal.pause()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
