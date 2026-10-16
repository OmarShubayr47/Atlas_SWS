"""Live check: how strongly do the wake-word models respond to a spoken phrase?

Listens for a fixed window (or re-scores a saved WAV with --wav), splits the
audio into tries by loudness, and prints each utterance's peak score per model (trigger level 0.5). The
whole window is saved as a WAV under scratch/wake_samples/ so the clips can
be reused as real test or training data.

Stop the assistant first — the mic cannot be opened twice:
    systemctl --user stop sws-assistant
    .venv/bin/python tests/wake_phrase_scores.py --label ya_atlas --seconds 60
    .venv/bin/python tests/wake_phrase_scores.py --wav scratch/wake_samples/<file>.wav
    systemctl --user start sws-assistant
"""
import argparse
import os
from pathlib import Path
import sys
import time
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "software"))
from common import mic_stream, wake_word  # noqa: E402

RATE = 16000
CHUNK_MS = wake_word.CHUNK_MS          # 80 ms = 1280 samples
CHUNK = RATE * CHUNK_MS // 1000
TAIL_CHUNKS = 8                        # the model peaks just after the word ends
RISE_DB = 15                           # "speech" = this far above the noise floor


def score_chunks(chunks, names):
    """Run the models over 80 ms chunks; returns (level_db, scores) per chunk."""
    model = wake_word.Model(wakeword_model_paths=[wake_word._model_path(n) for n in names])
    rows = []
    for c in chunks:
        a = np.frombuffer(c, dtype=np.int16)
        level = 20 * np.log10(np.sqrt(np.mean(a.astype(float) ** 2)) / 32768 + 1e-9)
        rows.append((level, {k: float(v) for k, v in model.predict(a).items()}))
    return rows


def report(rows):
    """Split on loudness (webrtcvad merged tries in this room's noise floor)."""
    levels = np.array([r[0] for r in rows])
    loud = levels > np.percentile(levels, 20) + RISE_DB
    keys = list(rows[0][1])
    tries, i = [], 0
    while i < len(rows):
        if not loud[i]:
            i += 1
            continue
        j = i
        while j < len(rows) and (loud[j] or loud[j:j + 4].any()):   # bridge <0.3 s dips
            j += 1
        window = rows[i:min(len(rows), j + TAIL_CHUNKS)]
        peak = {k: max(r[1][k] for r in window) for k in keys}
        tries.append(peak)
        marks = "  ".join(f"{k} {v:.2f}{' FIRE' if v >= wake_word.DEFAULT_THRESHOLD else ''}"
                          for k, v in peak.items())
        print(f"  #{len(tries):2d} at {i * CHUNK_MS / 1000:5.1f} s, peak {levels[i:j].max():4.0f} dBFS   {marks}")
        i = j
    for k in keys:
        fired = sum(t[k] >= wake_word.DEFAULT_THRESHOLD for t in tries)
        print(f"{k}: fired on {fired} of {len(tries)} tries")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", help="what is being said, e.g. ya_atlas (live mode)")
    ap.add_argument("--wav", help="re-score a saved 16 kHz mono recording instead of listening")
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--models", default="hey_atlas")
    ap.add_argument("--mic", default=os.environ.get("MIC_NAME_HINT", "CORSAIR"))
    args = ap.parse_args()
    names = [m.strip() for m in args.models.split(",") if m.strip()]

    if args.wav:
        with wave.open(args.wav) as w:
            data = w.readframes(w.getnframes())
        chunks = [data[i:i + CHUNK * 2] for i in range(0, len(data) - CHUNK * 2 + 1, CHUNK * 2)]
        report(score_chunks(chunks, names))
        return
    if not args.label:
        ap.error("--label is required when listening live")

    chunks = []
    print(f"Listening {args.seconds:.0f} s for '{args.label}' — speak now, pause ~2 s between tries.",
          flush=True)
    start = time.monotonic()
    with mic_stream.MicStream(args.mic) as mic:
        while time.monotonic() - start < args.seconds:
            chunks.append(mic.read_ms(CHUNK_MS))

    out = ROOT / "scratch" / "wake_samples"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{args.label}_{time.strftime('%Y%m%d_%H%M%S')}.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(b"".join(chunks))
    print(f"Saved {path.relative_to(ROOT)}")
    report(score_chunks(chunks, names))


if __name__ == "__main__":
    main()
