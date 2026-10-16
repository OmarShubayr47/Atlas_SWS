"""Live mic noise meter: find what is injecting mains hum.

Context: the assistant stopped detecting end-of-speech. Measured cause: the
"silent" room reads about -30 dBFS, ~80% of it in the 40-70 Hz band, with a
clean 60/120/240/360/480/600 Hz series — mains hum on the mic path, which
webrtcvad classifies as speech 100% of the time at every aggressiveness.

This prints a line every 2 seconds. Keep quiet, then change ONE thing at a
time and watch the numbers:

    1. switch off / unplug the amp's 5 V bench supply
    2. unplug the projector
    3. move the headset cable away from power bricks and mains leads
    4. try the headset in a different USB port

When the hum column collapses, that change removed the source.

Columns:
    level   overall dBFS (a quiet room on this headset should be well
            below the ~-30 dBFS measured with the hum)
    hum     share of energy at 60 Hz and its harmonics
    vad     % of frames webrtcvad (mode 2) calls speech — the number that
            actually breaks the assistant; should be near 0% when quiet

Usage:
    .venv/bin/python3 tests/mic_noise_monitor.py      (Ctrl+C to stop)
"""
import pathlib
import sys

import numpy as np
import webrtcvad

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "software"))

from common.mic_stream import MicStream  # noqa: E402

RATE = 16000
FRAME_MS = 30
WINDOW_S = 2.0
MAINS_HZ = 60.0          # measured fundamental on this supply
HARMONICS = 10


def hum_share(x: np.ndarray) -> float:
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / RATE)
    hum = 0.0
    for k in range(1, HARMONICS + 1):
        hum += spec[np.abs(freqs - k * MAINS_HZ) < 3].sum()
    total = spec[freqs > 20].sum()
    return hum / total if total else 0.0


def main() -> int:
    print("mic noise monitor — stay quiet, change ONE thing at a time")
    print(f"{'time':>5}  {'level':>9}  {'hum':>5}  {'vad':>5}  verdict")
    vad = webrtcvad.Vad(2)
    frame_bytes = RATE * FRAME_MS // 1000 * 2
    t = 0.0
    try:
        with MicStream("CORSAIR", target_rate=RATE) as mic:
            for _ in range(10):                      # prime, as vad_recorder does
                vad.is_speech(mic.read_ms(FRAME_MS), RATE)
            while True:
                raw = mic.read_ms(int(WINDOW_S * 1000))
                x = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
                x -= x.mean()
                rms = np.sqrt(np.mean(x ** 2))
                dbfs = 20 * np.log10(max(rms, 1) / 32768)
                frames = [raw[i:i + frame_bytes]
                          for i in range(0, len(raw) - frame_bytes + 1, frame_bytes)]
                speech = sum(vad.is_speech(f, RATE) for f in frames) / len(frames)
                share = hum_share(x)
                t += WINDOW_S
                if speech > 0.5 and share > 0.5:
                    verdict = "HUM — VAD fooled"
                elif speech > 0.5:
                    verdict = "sound (speech/noise?)"
                else:
                    verdict = "OK — silence detectable"
                print(f"{t:5.0f}s  {dbfs:6.1f}dBFS  {share:4.0%}  {speech:4.0%}  {verdict}",
                      flush=True)
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
