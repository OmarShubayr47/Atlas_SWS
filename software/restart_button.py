"""Restart button (GPIO27): hold to restart the SWS software, keep holding to reboot.

Tiered (owner decision, 2026-10-01; the 2 s reboot was verified 2026-09-21):

    released before 2 s          nothing (a brush or a bounce)
    held 2 s, then released      restart the SWS services: assistant, UI
                                 server and kiosk. Takes seconds and fixes
                                 most hangs without a full reboot.
    held 8 s                     orderly reboot of the Pi (the old behaviour)

A separate process from the voice assistant ON PURPOSE. The moment you most
need a restart button is when the assistant has hung — and a button handled
inside the assistant hangs with it. As its own small process it keeps working
whatever state the rest of the system is in. It also never restarts itself.

Safety choices:

  hold, not press  a 2 s hold is required for anything to happen. A brush
                   against the panel, or a bounce, must not restart or reboot
                   the machine. For a control with no screen, a sustained hold
                   is the cheapest available confirmation gate — and the
                   longer, more drastic action needs the longer hold.

  orderly reboot   /sbin/reboot resolves to systemctl on this Pi (verified),
                   which stops services and flushes filesystems. A hard power
                   cut risks corrupting the SD card; this does not.

  checked at start sudo must work non-interactively, or the reboot silently
                   hangs on a password prompt nobody can type — a failure that
                   never shows when testing from a terminal. This checks at
                   startup and says so immediately. If it fails, the reboot
                   tier is disabled but the software restart still works.

  dry run          --dry-run does everything except restart/reboot, for bench
                   testing.

The projected UI shows what a hold will do ("release: restart software ·
keep holding: reboot") through the same fire-and-forget events the assistant
uses, so it still works when the UI is down.

Wiring: momentary switch between GPIO27 (pin 13) and GND, internal pull-up.
On the HAT's TS365ZJ, pins 1 & 3 are the switch contacts; 2 & 4 are shell
ground only.

Usage:
    python software/restart_button.py --dry-run     # test, never restarts
    python software/restart_button.py               # live
"""
import os
import signal
import subprocess
import sys
import threading
import time

from gpiozero import Button

try:  # optional: same .env as the assistant (UI_PORT, hold times)
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from common import ui_events  # noqa: E402

RESTART_PIN = int(os.environ.get("RESTART_PIN", "27"))
# RESTART_HOLD_S keeps its old meaning: the first (shortest) hold that acts.
SOFT_HOLD_S = float(os.environ.get("RESTART_HOLD_S", "2.0"))
REBOOT_HOLD_S = float(os.environ.get("RESTART_REBOOT_HOLD_S", "8.0"))
# Matches the project's debounce convention (>=5 ms).
BOUNCE_S = 0.005
SERVICES = os.environ.get(
    "RESTART_SERVICES", "sws-assistant.service sws-ui.service sws-kiosk.service"
).split()
SOFT_CMD = ["systemctl", "--user", "restart", *SERVICES]
REBOOT_CMD = ["sudo", "-n", "/sbin/reboot"]


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sudo_ready() -> bool:
    """True if the reboot will run without a password prompt.

    `sudo -n -l <cmd>` asks whether the command is permitted without actually
    running it, so this check can never reboot the machine by accident.
    """
    try:
        r = subprocess.run(["sudo", "-n", "-l", "/sbin/reboot"],
                           capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


class TieredRestart:
    """The hold logic, separate from GPIO so the stages are easy to follow."""

    def __init__(self, button, dry_run: bool, reboot_allowed: bool):
        self.button = button
        self.dry_run = dry_run
        self.reboot_allowed = reboot_allowed
        self._lock = threading.Lock()
        self._stage = "idle"   # idle | holding | armed | rebooting
        self._hold = 0         # increments per press/release: stale timers quit

    def on_press(self) -> None:
        with self._lock:
            self._stage = "holding"
            self._hold += 1
            hold = self._hold
        _log(f"pressed — hold {SOFT_HOLD_S:.0f}s to restart the software, "
             f"{REBOOT_HOLD_S:.0f}s to reboot")
        ui_events.publish("restart", stage="holding", soft_s=SOFT_HOLD_S,
                          reboot_s=REBOOT_HOLD_S if self.reboot_allowed else None)
        threading.Thread(target=self._reboot_timer, args=(hold,),
                         daemon=True).start()

    def on_held(self) -> None:
        """gpiozero fires this once the button has been held SOFT_HOLD_S."""
        with self._lock:
            if self._stage != "holding":
                return
            self._stage = "armed"
        tail = (f"keep holding to {REBOOT_HOLD_S:.0f}s to reboot"
                if self.reboot_allowed else "reboot tier disabled (sudo)")
        _log(f"HELD {SOFT_HOLD_S:.0f}s — release now to restart the software; {tail}")
        ui_events.publish("restart", stage="armed")

    def on_release(self) -> None:
        with self._lock:
            stage = self._stage
            self._stage = "idle" if stage != "rebooting" else stage
            self._hold += 1
        if stage == "holding":
            _log("released early — nothing done")
            ui_events.publish("restart", stage="cancelled")
        elif stage == "armed":
            threading.Thread(target=self._restart_software, daemon=True).start()

    def _reboot_timer(self, hold: int) -> None:
        if not self.reboot_allowed:
            return
        deadline = time.monotonic() + REBOOT_HOLD_S
        while time.monotonic() < deadline:
            time.sleep(0.05)
            with self._lock:
                if self._hold != hold:
                    return               # released (or a newer press)
        with self._lock:
            if self._hold != hold or not self.button.is_pressed:
                return
            self._stage = "rebooting"
        self._reboot()

    def _restart_software(self) -> None:
        ui_events.publish("restart", stage="software")
        if self.dry_run:
            _log(f"would now run: {' '.join(SOFT_CMD)}  (dry run)")
            return
        _log(f"restarting the software: {' '.join(SOFT_CMD)}")
        try:
            r = subprocess.run(SOFT_CMD, capture_output=True, text=True, timeout=90)
            if r.returncode == 0:
                _log("software restart issued")
            else:
                _log(f"!! software restart failed ({r.returncode}): "
                     f"{(r.stderr or r.stdout).strip()[:300]}")
        except Exception as e:  # noqa: BLE001 - the button must keep working
            _log(f"!! software restart failed: {type(e).__name__}: {e}")

    def _reboot(self) -> None:
        ui_events.publish("restart", stage="reboot")
        if self.dry_run:
            _log(f"HELD {REBOOT_HOLD_S:.0f}s — would now run: {' '.join(REBOOT_CMD)}")
            _log("(dry run: not rebooting)")
            return
        _log(f"HELD {REBOOT_HOLD_S:.0f}s — rebooting now")
        subprocess.run(REBOOT_CMD)


def main() -> int:
    dry_run = "--dry-run" in sys.argv or os.environ.get("RESTART_DRY_RUN") == "1"

    _log(f"restart button on GPIO{RESTART_PIN}: hold {SOFT_HOLD_S:.0f}s = restart "
         f"software, {REBOOT_HOLD_S:.0f}s = reboot"
         f"{'  [DRY RUN — will not restart or reboot]' if dry_run else ''}")

    reboot_allowed = True
    if not sudo_ready():
        _log("!! sudo cannot run /sbin/reboot without a password.")
        _log("   The reboot tier would appear to work and then hang silently,")
        _log("   so it is DISABLED; the software-restart tier still works.")
        _log("   Fix: sudo visudo -f /etc/sudoers.d/swspi-reboot")
        _log("        swspi ALL=(root) NOPASSWD: /sbin/reboot")
        reboot_allowed = dry_run   # a dry run can still show the timing
    else:
        _log("sudo check OK: reboot will run non-interactively")

    try:
        btn = Button(RESTART_PIN, pull_up=True, bounce_time=BOUNCE_S,
                     hold_time=SOFT_HOLD_S)
    except Exception as e:
        _log(f"!! could not claim GPIO{RESTART_PIN}: {type(e).__name__}: {e}")
        return 1

    tiers = TieredRestart(btn, dry_run=dry_run, reboot_allowed=reboot_allowed)
    btn.when_pressed = tiers.on_press
    btn.when_released = tiers.on_release
    btn.when_held = tiers.on_held

    _log("ready")
    signal.signal(signal.SIGINT, lambda *_: (_log("stopped"), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda *_: (_log("stopped"), sys.exit(0)))
    signal.pause()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
