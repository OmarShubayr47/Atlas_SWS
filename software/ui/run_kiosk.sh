#!/usr/bin/env bash
# Start the projected UI: the local UI server (if not already up) and Chromium
# in kiosk mode on the Pi's desktop session. Works from SSH as well as locally.
#
#   software/ui/run_kiosk.sh          start
#   pkill -x chromium                 close the kiosk (server keeps running)
set -euo pipefail
cd "$(dirname "$0")/../.."

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
PORT="${UI_PORT:-8765}"
URL="http://127.0.0.1:${PORT}/"

if [ "${SWS_MANAGED:-0}" = "1" ]; then
    # Started by systemd (software/deploy/systemd/sws-kiosk.service). The UI
    # server is its own unit, so wait for it rather than start a second one;
    # and with linger this can run before the desktop session exists, so wait
    # for its Wayland socket too. Exiting non-zero lets systemd retry.
    for _ in $(seq 1 120); do [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ] && break; sleep 1; done
    [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ] || { echo "No Wayland socket $XDG_RUNTIME_DIR/$WAYLAND_DISPLAY"; exit 1; }
    for _ in $(seq 1 60); do curl -fs "${URL}health" >/dev/null && break; sleep 0.5; done
    curl -fs "${URL}health" >/dev/null || { echo "UI server (sws-ui.service) not answering"; exit 1; }
elif ! curl -fs "${URL}health" >/dev/null; then
    mkdir -p scratch
    nohup .venv/bin/python3 software/ui/server.py > scratch/ui_server.log 2>&1 &
    for _ in $(seq 1 20); do curl -fs "${URL}health" >/dev/null && break; sleep 0.25; done
fi
curl -fs "${URL}health" >/dev/null || { echo "UI server did not start; see scratch/ui_server.log"; exit 1; }

# Flags: kiosk + no first-run/keyring/crash-restore dialogs, which would
# otherwise sit on the projection with no keyboard to dismiss them; scale 1 so
# CSS pixels are panel pixels; no pinch-zoom or swipe-navigation, which a
# touch surface would otherwise trigger by accident.
exec chromium "--app=${URL}" --kiosk --ozone-platform=wayland \
    --user-data-dir="$HOME/.config/sws-kiosk" --password-store=basic \
    --no-first-run --noerrdialogs --disable-infobars \
    --disable-session-crashed-bubble --hide-crash-restore-bubble \
    --check-for-update-interval=31536000 \
    --force-device-scale-factor=1 --disable-pinch --overscroll-history-navigation=0
