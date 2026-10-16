"""Suppress ALSA/PortAudio C-level stderr spam during device enumeration.

Opening PyAudio on this Pi prints ~40 lines of noise before anything useful
happens: ALSA evaluating surround51/iec958/hdmi PCM definitions that don't
apply to a 2-channel USB card, plus JACK failing to find a server that was
never running. None of it is actionable, and it buries the messages that
*are* (device-not-found, wrong card, permissions).

It can't be filtered with `warnings` or by reassigning sys.stderr, because
it's written by C libraries straight to file descriptor 2, below Python's
view. So redirect the fd itself.

Deliberately scoped to initialisation only — see MicStream. Wrapping the
whole program would hide genuine runtime errors, which is exactly the
failure mode this is trying to fix.
"""
import contextlib
import os
import sys


@contextlib.contextmanager
def suppressed_c_stderr():
    """Redirect fd 2 to /dev/null for the duration of the block.

    Restores the original fd afterwards even if the block raises, so an
    exception during init still reports normally.
    """
    sys.stderr.flush()
    saved_fd = os.dup(2)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull_fd, 2)
        yield
    finally:
        sys.stderr.flush()
        os.dup2(saved_fd, 2)
        os.close(devnull_fd)
        os.close(saved_fd)
