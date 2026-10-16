"""Bench test: does a continuous tone stay continuous at the SPEAKER?

Why: Atlas's spoken replies were heard cutting out roughly every 0.5 s
(owner, 2026-09-29). keepalive_output.py now logs, per reply, whether the
network delivered speech slower than it plays (silence inserted mid-reply).
This test answers the other half of the question: with the network taken
out entirely — a locally generated tone, written all at once like a fast TTS
stream — does the sound still drop out somewhere between aplay and the
projector's speaker?

    tone continuous here + gaps in the reply logs  -> network delivery (fix:
                                                      prebuffer/jitter buffer)
    tone drops out here                             -> ALSA/HDMI/projector side
    neither                                         -> keep logging real use

Method: open the same KeepAliveOutput the assistant uses, let it run silence
for a few seconds (the projector drops the first seconds of a NEW stream),
then play a 1 kHz tone while the USB mic records the room. The tone's level
is measured every 20 ms with a single-frequency filter (Goertzel), so room
noise and speech barely count. A frame more than DROP_DB below the tone's
median level counts as a dropout.

The assistant must be stopped first — it owns the mic and the HDMI device:
    systemctl --user stop sws-assistant
    .venv/bin/python tests/playback_continuity_test.py [--seconds 10] [--device PCM]
    systemctl --user start sws-assistant

Put the mic within about a metre of the projector's speaker. The tone plays
at -20 dBFS through the same path as speech, so check the projector volume
is comfortable before starting. A WAV of the recording goes to scratch/.
"""
import argparse
import os
import pathlib
import subprocess
import sys
import threading
import time
import wave

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "software"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)
os.environ["UI_EVENTS"] = "0"

from common import keepalive_output, mic_stream  # noqa: E402

TONE_HZ = 1000
TONE_DBFS = -20.0
WARMUP_S = 6.0          # silence first: the projector mutes new streams
FRAME_MS = 20
DROP_DB = 12.0          # this far below the median tone level = dropout


def make_tone(seconds: float) -> bytes:
    rate = keepalive_output.RATE
    t = np.arange(int(rate * seconds)) / rate
    amp = 10 ** (TONE_DBFS / 20)
    x = np.sin(2 * np.pi * TONE_HZ * t) * amp
    fade = int(rate * 0.01)                       # no click at either end
    ramp = (1 - np.cos(np.linspace(0, np.pi, fade))) / 2
    x[:fade] *= ramp
    x[-fade:] *= ramp[::-1]
    return (x * 32767).astype("<i2").tobytes()


def goertzel_db(frame: np.ndarray, rate: int, freq: float) -> float:
    """Level of one frequency in one frame, in dB (relative)."""
    k = 2 * np.cos(2 * np.pi * freq / rate)
    s_prev = s_prev2 = 0.0
    for x in frame:
        s = x + k * s_prev - s_prev2
        s_prev2, s_prev = s_prev, s
    power = s_prev2 ** 2 + s_prev ** 2 - k * s_prev * s_prev2
    return 10 * np.log10(power / len(frame) + 1e-9)


def record(mic_hint: str, seconds: float, out: list, ready: threading.Event):
    with mic_stream.MicStream(mic_hint) as mic:
        ready.set()
        n = int(seconds * 1000 / FRAME_MS)
        for _ in range(n):
            out.append(mic.read_ms(FRAME_MS))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--device", default=os.environ.get("PLAYBACK_PCM", "").strip())
    args = ap.parse_args()
    if not args.device:
        print("No playback device: set PLAYBACK_PCM in .env or pass --device.")
        return 1

    active = subprocess.run(["systemctl", "--user", "is-active", "sws-assistant"],
                            capture_output=True, text=True).stdout.strip()
    if active == "active":
        print("The assistant service is running and owns the mic and HDMI audio.")
        print("Stop it first:  systemctl --user stop sws-assistant")
        return 1

    mic_hint = os.environ.get("MIC_NAME_HINT", "CORSAIR")
    print(f"Output {args.device}; tone {TONE_HZ} Hz at {TONE_DBFS:.0f} dBFS "
          f"for {args.seconds:.0f} s after {WARMUP_S:.0f} s of silence.")
    out = keepalive_output.KeepAliveOutput(args.device)
    frames: list[bytes] = []
    ready = threading.Event()
    total = WARMUP_S + args.seconds + 2.0
    rec = threading.Thread(target=record, args=(mic_hint, total, frames, ready))
    rec.start()
    ready.wait(10)
    time.sleep(WARMUP_S)
    t_tone = time.monotonic()
    out.begin()
    out.write(make_tone(args.seconds))     # all at once, like a fast stream
    out.drain()
    print(f"Tone written and drained in {time.monotonic() - t_tone:.1f} s.")
    rec.join()

    pcm = b"".join(frames)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    wav_path = ROOT / "scratch" / f"playback_continuity_{stamp}.wav"
    wav_path.parent.mkdir(exist_ok=True)
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(mic_stream.TARGET_RATE)
        wf.writeframes(pcm)

    x = np.frombuffer(pcm, dtype="<i2").astype(np.float64)
    step = int(mic_stream.TARGET_RATE * FRAME_MS / 1000)
    levels = np.array([goertzel_db(x[i:i + step], mic_stream.TARGET_RATE, TONE_HZ)
                       for i in range(0, len(x) - step, step)])
    noise = np.median(levels[: int(WARMUP_S * 1000 / FRAME_MS) - 10])
    loud = np.where(levels > noise + 15)[0]
    if len(loud) == 0:
        print(f"Tone NOT detected at the mic (noise floor {noise:.0f} dB). "
              f"Check the projector volume and mic placement. WAV: {wav_path}")
        return 2
    region = levels[loud[0]:loud[-1] + 1]
    median = np.median(region)
    drops = region < median - DROP_DB
    events, longest, run = 0, 0, 0
    for d in drops:
        run = run + 1 if d else 0
        if run == 1:
            events += 1
        longest = max(longest, run)
    heard_s = len(region) * FRAME_MS / 1000
    print(f"Tone heard for {heard_s:.1f} s of {args.seconds:.1f} s; "
          f"{(median - noise):.0f} dB above the room.")
    print(f"Dropouts (> {DROP_DB:.0f} dB down for >= {FRAME_MS} ms): {events}, "
          f"total {drops.sum() * FRAME_MS} ms, longest {longest * FRAME_MS} ms.")
    print("RESULT:", "CONTINUOUS" if events == 0 else "DROPOUTS AT THE SPEAKER",
          f"— recording: {wav_path}")
    return 0 if events == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
