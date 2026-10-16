"""Tell systemd how the process is doing: started, still alive, stopping.

Under a `Type=notify` unit, systemd waits for "READY=1" before it considers
the service started, and with `WatchdogSec=` set it expects "WATCHDOG=1" at
least that often — if the pings stop, it kills the process and `Restart=`
brings up a fresh one. That turns a HANG into a restart, which plain
`Restart=always` cannot do: it only notices a process that exits.

The protocol is one datagram on the unix socket named in $NOTIFY_SOCKET, so
this is a few lines of standard library rather than a dependency on
systemd-python. Outside systemd (a manual run in a terminal) $NOTIFY_SOCKET
is unset and every call is a silent no-op, so the same code runs both ways.
"""
import os
import socket


def notify(message: str) -> bool:
    """Send one notification, e.g. "READY=1". True if it was delivered.

    Never raises: losing a notification must not take the assistant down.
    """
    address = os.environ.get("NOTIFY_SOCKET")
    if not address:
        return False
    # A leading "@" means a Linux abstract-namespace socket, written with a
    # NUL first byte at the socket API level.
    if address.startswith("@"):
        address = "\0" + address[1:]
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(address)
            sock.sendall(message.encode())
        return True
    except OSError:
        return False


def watchdog_interval_s() -> float | None:
    """How often systemd wants a WATCHDOG=1 ping, or None if it doesn't.

    systemd exports the configured WatchdogSec as $WATCHDOG_USEC. Pinging at
    half that interval is its documented recommendation, so one late ping is
    not fatal.
    """
    raw = os.environ.get("WATCHDOG_USEC")
    if not raw:
        return None
    try:
        return int(raw) / 1_000_000 / 2
    except ValueError:
        return None
