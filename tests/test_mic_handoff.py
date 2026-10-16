"""Regression test: stream handoff must not crash the process.

Reproduces the pattern that killed voice_realtime.py with SIGABRT. Each
MicStream used to construct its own pyaudio.PyAudio(); since Pa_Initialize
and Pa_Terminate are process-global rather than per-object, one stream
closing in one thread tore PortAudio down underneath another stream opening
in a different thread. The process aborted inside the first read, and because
a USB isochronous endpoint was live at the time, the controller was left
mid-transfer and the kernel dropped the device off the bus.

This exercises the handoff hard: a background thread repeatedly opens,
reads and closes a 16kHz stream (the wake-word pattern) while the main
thread repeatedly opens, reads and closes a 24kHz stream (the Realtime
session pattern).

A Python exception here is a normal failure. A SIGABRT is the bug: the
process dies with no traceback and the test reports nothing, so treat
"no output / Aborted" as a failure regardless of exit code.

Usage:
    .venv/bin/python3 tests/test_mic_handoff.py [cycles]
"""
import pathlib
import sys
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "software"))

from common.mic_stream import MicStream  # noqa: E402

errors: list[str] = []


def _wake_word_pattern(stop: threading.Event, stats: dict) -> None:
    """Open/read/close at 16kHz repeatedly, like the wake-word listener."""
    while not stop.is_set():
        try:
            with MicStream("CORSAIR", target_rate=16000) as m:
                for _ in range(5):
                    m.read_ms(80)
                    if stop.is_set():
                        break
            stats["cycles"] += 1
        except OSError:
            # Contended open is expected and handled; not a failure.
            stats["contended"] += 1
            time.sleep(0.05)
        except Exception as e:
            errors.append(f"wake-word thread: {type(e).__name__}: {e}")
            return


def main() -> int:
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 15

    print(f"handoff stress: {cycles} cycles of 24kHz open/close in the main")
    print("thread while a background thread cycles 16kHz streams")
    print("(pre-fix this aborted the process within ~1s)\n")

    stop = threading.Event()
    bg_stats = {"cycles": 0, "contended": 0}
    bg = threading.Thread(target=_wake_word_pattern, args=(stop, bg_stats), daemon=True)
    bg.start()

    main_ok = 0
    contended = 0
    try:
        for i in range(cycles):
            try:
                with MicStream("CORSAIR", target_rate=24000) as m:
                    for _ in range(3):
                        m.read_ms(40)
                main_ok += 1
            except OSError:
                contended += 1
            if (i + 1) % 5 == 0:
                print(f"  cycle {i+1:3d}/{cycles}  main ok={main_ok} contended={contended}  "
                      f"bg ok={bg_stats['cycles']} contended={bg_stats['contended']}")
            time.sleep(0.05)
    finally:
        stop.set()
        bg.join(timeout=5)

    print()
    if errors:
        for e in errors:
            print(f"FAIL {e}")
        return 1

    print(f"SURVIVED — process alive after {cycles} handoff cycles")
    print(f"  main thread: {main_ok} ok, {contended} cleanly contended")
    print(f"  bg thread  : {bg_stats['cycles']} ok, {bg_stats['contended']} cleanly contended")
    print("\nNo SIGABRT: the shared-PortAudio-instance fix holds.")
    print("'Cleanly contended' means the device was busy and PortAudio said so")
    print("through a normal OSError, which is correct behaviour, not a fault.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
