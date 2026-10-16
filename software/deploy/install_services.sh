#!/usr/bin/env bash
# Install, or remove, the Smart Working Station systemd USER services:
#
#   sws-ui         projected-UI server
#   sws-assistant  voice assistant (watchdog-supervised)
#   sws-restart    restart button (GPIO27)
#   sws-kiosk      Chromium kiosk on the projector
#
#   software/deploy/install_services.sh               install, enable, (re)start
#   software/deploy/install_services.sh --uninstall   stop, disable, remove
#
# Why USER services: the kiosk has to live in the desktop's Wayland session
# anyway, one kind of unit is simpler to learn, and they are managed without
# sudo. "Linger" makes the user's service manager start at boot, without
# waiting for a login, and keep running after a logout.
#
# The unit files are SYMLINKED from the repo, so a `git pull` that changes one
# takes effect after:  systemctl --user daemon-reload
#                      systemctl --user restart <unit>
#
# Day-to-day commands:
#   systemctl --user status 'sws-*'
#   journalctl --user-unit=sws-assistant -f        (-b for this boot only)
#   systemctl --user stop sws-assistant          (before any manual test run)
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
UNIT_SRC="$REPO/software/deploy/systemd"
UNIT_DST="$HOME/.config/systemd/user"
UNITS=(sws-ui.service sws-assistant.service sws-restart.service sws-kiosk.service)
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

if [ "${1:-}" = "--uninstall" ]; then
    systemctl --user disable --now "${UNITS[@]}" 2>/dev/null || true
    for u in "${UNITS[@]}"; do rm -f "$UNIT_DST/$u"; done
    systemctl --user daemon-reload
    echo "SWS services removed. Linger is left on; to undo it:"
    echo "  sudo loginctl disable-linger $USER"
    exit 0
fi

[ -x "$REPO/.venv/bin/python" ] || { echo "No virtualenv at $REPO/.venv"; exit 1; }
[ "$REPO" = "$HOME/sws" ] || { echo "Units expect the repo at ~/sws (found $REPO)"; exit 1; }

# Refuse while SWS programs run by hand: a second copy would fight the
# service over the GPIO pins, the microphone and the HDMI audio device, and a
# second kiosk would just pile up Chromium windows. Service-run processes are
# recognised by their systemd cgroup and are fine (re-running this script).
conflicts=""
pattern='software/(voice_assistant|voice_control|voice_realtime|restart_button)\.py|software/ui/server\.py|sws-kiosk'
for pid in $(pgrep -f "$pattern" || true); do
    [ "$pid" = "$$" ] && continue
    if ! grep -qE 'sws-[a-z]+\.service' "/proc/$pid/cgroup" 2>/dev/null; then
        conflicts+="  $(ps -o pid=,args= -p "$pid" 2>/dev/null | cut -c1-110)"$'\n'
    fi
done
if [ -n "$conflicts" ]; then
    echo "Stop these hand-started SWS processes first (Ctrl-C them, or kill <pid>):"
    printf '%s' "$conflicts"
    exit 1
fi

mkdir -p "$UNIT_DST"
for u in "${UNITS[@]}"; do
    ln -sfn "$UNIT_SRC/$u" "$UNIT_DST/$u"
done
systemctl --user daemon-reload
systemctl --user enable "${UNITS[@]}"

if [ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null)" != "yes" ]; then
    echo "Enabling linger so the services start at boot without a login..."
    loginctl enable-linger "$USER" 2>/dev/null || sudo loginctl enable-linger "$USER"
fi

systemctl --user restart "${UNITS[@]}"
sleep 4
echo
for u in "${UNITS[@]}"; do
    printf '%-24s %s\n' "$u" "$(systemctl --user is-active "$u" || true)"
done
echo
echo "Logs: journalctl --user-unit=sws-assistant -f"
