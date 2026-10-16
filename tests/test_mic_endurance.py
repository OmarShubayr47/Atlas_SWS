"""Isolate whether continuous capture alone kills the USB mic.

Context: the mic repeatedly dropped off the USB bus during Realtime sessions
with `xhci-hcd: WARN: buffer overrun event ... on endpoint` followed by
`usb usb1-port2: disabled by hub (EMI?)`. Two candidate causes: the
application's timing (network I/O interleaved with capture), or something
electrical/physical independent of software.

This test removes every software variable — no WebSocket, no asyncio, no
threads, no wake word, no playback. Just one stream, read continuously, for
as long as asked. It answers one question:

    does sustained capture on its own reproduce the disconnect?

  survives  -> capture alone is fine; suspicion returns to what the
               application adds on top (concurrency, a second stream being
               opened, playback running at the same time)
  dies      -> the fault is below the application entirely; the fix is
               physical (port, cable, power, EMI), not code

Usage:
    .venv/bin/python3 tests/test_mic_endurance.py [seconds] [target_rate]
"""
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "software"))

from common.mic_stream import MicStream  # noqa: E402

CHUNK_MS = 40  # matches voice_realtime.py's MIC_CHUNK_MS


def main() -> int:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    rate = int(sys.argv[2]) if len(sys.argv) > 2 else 24000

    print(f"capturing continuously for {seconds:.0f}s at {rate} Hz "
          f"({CHUNK_MS}ms chunks), no network, no threads")
    print("if the mic survives this, sustained capture is not the cause\n")

    started = time.monotonic()
    chunks = 0
    silent_chunks = 0
    last_report = started

    try:
        with MicStream("CORSAIR", target_rate=rate) as mic:
            print(f"stream open (native {mic.native_rate} Hz -> {rate} Hz)\n")
            while time.monotonic() - started < seconds:
                data = mic.read_ms(CHUNK_MS)
                chunks += 1
                arr = np.frombuffer(data, dtype=np.int16)
                if not arr.any():
                    silent_chunks += 1

                now = time.monotonic()
                if now - last_report >= 5:
                    elapsed = now - started
                    expected = elapsed * 1000 / CHUNK_MS
                    print(f"  t={elapsed:5.1f}s  chunks={chunks:6d}  "
                          f"expected~{expected:6.0f}  peak={int(np.abs(arr).max()):6d}  "
                          f"all-zero chunks={silent_chunks}")
                    last_report = now
    except Exception as e:
        elapsed = time.monotonic() - started
        print(f"\nFAILED after {elapsed:.1f}s and {chunks} chunks")
        print(f"  {type(e).__name__}: {e}")
        print("\n-> sustained capture alone reproduces the fault.")
        print("   Check `dmesg | tail` for a USB disconnect; if present the")
        print("   cause is below the application and the fix is physical.")
        return 1

    elapsed = time.monotonic() - started
    print(f"\nSURVIVED {elapsed:.1f}s, {chunks} chunks, "
          f"{silent_chunks} all-zero")
    print("-> capture alone is not the trigger; look at what the app adds")
    print("   on top (concurrent streams, playback, session teardown).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
