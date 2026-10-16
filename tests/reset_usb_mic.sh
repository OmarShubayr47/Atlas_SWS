#!/usr/bin/env bash
# Re-enumerate the USB mic without physically unplugging it.
#
# When the hub disables the port ("disabled by hub (EMI?)" in dmesg) the
# device vanishes from lsusb and ALSA. Unbinding and rebinding the USB device
# through sysfs forces the kernel to enumerate it again, which is what a
# physical replug does — just without reaching behind the Pi.
#
# Usage:  sudo tests/reset_usb_mic.sh
set -euo pipefail

VENDOR_PRODUCT="1b1c:0a5f"   # Corsair HS60 HAPTIC

if [[ $EUID -ne 0 ]]; then
    echo "Needs root (sysfs bind/unbind): sudo $0" >&2
    exit 1
fi

# Find the sysfs device path whose idVendor/idProduct match.
target=""
for dev in /sys/bus/usb/devices/*; do
    [[ -f "$dev/idVendor" && -f "$dev/idProduct" ]] || continue
    id="$(cat "$dev/idVendor"):$(cat "$dev/idProduct")"
    if [[ "$id" == "$VENDOR_PRODUCT" ]]; then
        target="$(basename "$dev")"
        break
    fi
done

if [[ -z "$target" ]]; then
    echo "Device $VENDOR_PRODUCT is not on the USB bus at all."
    echo "The hub disabled the port entirely, so there is nothing to rebind."
    echo
    if [[ "${1:-}" == "--reset-controller" ]]; then
        # Last resort: rebind the whole xHCI host controller, forcing every
        # device on that bus to re-enumerate. Disruptive — any other USB
        # device (keyboard, storage) drops and comes back too. SSH survives:
        # on a Pi 5 neither Ethernet nor WiFi sits on this controller.
        echo "--reset-controller given; rebinding xhci-hcd.0 (ALL USB devices will re-enumerate)..."
        echo -n "xhci-hcd.0" > /sys/bus/platform/drivers/xhci-hcd/unbind || true
        sleep 2
        echo -n "xhci-hcd.0" > /sys/bus/platform/drivers/xhci-hcd/bind || true
        sleep 3
        echo "--- arecord -l ---"
        arecord -l | grep -i -A1 corsair || echo "(still absent — physical replug needed)"
        exit 0
    fi
    echo "Options:"
    echo "  1. Unplug and replug the headset (always works)."
    echo "  2. sudo $0 --reset-controller   # resets the whole USB bus"
    exit 1
fi

echo "Found $VENDOR_PRODUCT at $target — rebinding..."
echo -n "$target" > /sys/bus/usb/drivers/usb/unbind
sleep 1
echo -n "$target" > /sys/bus/usb/drivers/usb/bind
sleep 2

echo "--- arecord -l ---"
arecord -l | grep -i -A1 corsair || echo "(not back yet; give it a moment or replug)"
