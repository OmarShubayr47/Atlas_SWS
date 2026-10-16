"""Does concurrent network traffic during capture kill the USB mic?

tests/test_mic_endurance.py established that sustained capture alone is fine
(60s, 1489 chunks, no dropouts). The Realtime path differs from it in one
significant way: it streams audio over the network *while* capturing.

Two mechanisms could explain a disconnect from that:

  power  - WiFi transmit happens in bursts that draw meaningful current. On
           top of a bus-powered USB headset that can sag the port rail far
           enough for the hub to drop the device. The kernel reports this the
           same way it reports interference: "disabled by hub (EMI?)".
  timing - host CPU/interrupt load delaying servicing of the USB isochronous
           endpoint, producing "buffer overrun event ... on endpoint".

This test reproduces the load without the Realtime API, so it costs nothing:
capture continuously in a thread (as voice_realtime.py now does) while
uploading a comparable, continuous stream of bytes over the network.

  survives -> capture + network is fine; suspicion moves to the specific
              orchestration in voice_realtime.py (concurrent streams, the
              wake-word handoff, session teardown)
  dies     -> the combination itself is the trigger, and the fix is
              electrical: different port, shorter/shielded cable, powered
              hub, or moving the mic away from the cooler

Usage:
    .venv/bin/python3 tests/test_mic_with_network.py [seconds]
"""
import pathlib
import queue
import sys
import threading
import time

import numpy as np
import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "software"))

from common.mic_stream import MicStream  # noqa: E402

CHUNK_MS = 40
RATE = 24000
# Comparable to what the Realtime path uploads: 24kHz mono int16 at 40ms
# chunks is ~1920 bytes every 40ms, i.e. ~48 KB/s sustained.
UPLOAD_CHUNK = b"\0" * 1920
UPLOAD_INTERVAL_S = CHUNK_MS / 1000


def _network_load(stop: threading.Event, stats: dict) -> None:
    """Keep the radio busy with a sustained upload, mirroring the audio rate."""
    session = requests.Session()
    while not stop.is_set():
        try:
            # httpbin-style echo isn't needed; any endpoint that accepts a
            # POST body and is cheap to hit will exercise the radio.
            session.post("https://api.openai.com/v1/models",
                         data=UPLOAD_CHUNK, timeout=10)
            stats["requests"] += 1
        except Exception:
            stats["errors"] += 1
        time.sleep(UPLOAD_INTERVAL_S)


def _capture(stop: threading.Event, out: queue.Queue, stats: dict) -> None:
    try:
        with MicStream("CORSAIR", target_rate=RATE) as mic:
            stats["native_rate"] = mic.native_rate
            stats["open"] = True
            while not stop.is_set():
                data = mic.read_ms(CHUNK_MS)
                stats["chunks"] += 1
                arr = np.frombuffer(data, dtype=np.int16)
                stats["peak"] = int(np.abs(arr).max())
                if not arr.any():
                    stats["silent"] += 1
    except Exception as e:
        stats["error"] = f"{type(e).__name__}: {e}"
    finally:
        out.put(None)


def main() -> int:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    print(f"capture + concurrent network upload for {seconds:.0f}s")
    print("(no Realtime API; this costs nothing)\n")

    stop = threading.Event()
    cap_stats = {"chunks": 0, "silent": 0, "peak": 0, "open": False}
    net_stats = {"requests": 0, "errors": 0}
    done: queue.Queue = queue.Queue()

    cap = threading.Thread(target=_capture, args=(stop, done, cap_stats), daemon=True)
    net = threading.Thread(target=_network_load, args=(stop, net_stats), daemon=True)
    cap.start()
    net.start()

    started = time.monotonic()
    try:
        while time.monotonic() - started < seconds:
            time.sleep(5)
            elapsed = time.monotonic() - started
            if "error" in cap_stats:
                break
            print(f"  t={elapsed:5.1f}s  chunks={cap_stats['chunks']:6d}  "
                  f"net_req={net_stats['requests']:4d} (err {net_stats['errors']}) "
                  f" peak={cap_stats['peak']:6d}")
    finally:
        stop.set()
        cap.join(timeout=3)
        net.join(timeout=3)

    elapsed = time.monotonic() - started
    if "error" in cap_stats:
        print(f"\nFAILED after {elapsed:.1f}s, {cap_stats['chunks']} chunks")
        print(f"  {cap_stats['error']}")
        print("\n-> capture + network reproduces it. Check `dmesg | tail`.")
        print("   If a USB disconnect is there, the fix is electrical:")
        print("   different port, shielded/shorter cable, powered hub, or")
        print("   more distance from the active cooler.")
        return 1

    print(f"\nSURVIVED {elapsed:.1f}s, {cap_stats['chunks']} chunks, "
          f"{net_stats['requests']} network requests")
    print("-> capture + network is not the trigger either; the cause is")
    print("   specific to voice_realtime.py's orchestration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
