"""Where does the assistant's response time go? Stage-by-stage benchmark.

Runs the cloud stages on a FIXED input (the last real recording) so options
can be compared fairly, instead of guessing which stage to optimise:

    STT   transcription model A vs B
    LLM   default reasoning vs reduced reasoning effort
    TTS   time-to-first-audio: whole WAV file vs streamed raw PCM
    conv  local ffmpeg transcode of a reply (the current pipeline does this)

Network latency varies, so each variant runs more than once and the spread is
shown. Costs a few cents of API usage per run.

Usage:
    python tests/latency_bench.py
"""
import os
import pathlib
import statistics
import subprocess
import time

import requests
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
# Same DNS fix as the assistant: without it the first request in the process
# absorbs a 5 s resolver stall, which skewed the first version of this bench.
os.environ.setdefault("RES_OPTIONS", "single-request-reopen")
S = requests.Session()
KEY = os.environ["OPENAI_API_KEY"]
BASE = "https://api.openai.com/v1"
H = {"Authorization": f"Bearer {KEY}"}
WAV = ROOT / "scratch" / "assistant_input.wav"
RUNS = 3
SYSTEM = ("You are a helpful, witty, and concise AI voice assistant on a Raspberry "
          "Pi workstation. Respond naturally in brief sentences suitable for "
          "text-to-speech output.")
QUESTION = "Tell me about Ohm's law."
REPLY = ("Ohm's law says the current through a conductor equals the voltage "
         "across it divided by its resistance. Double the voltage, double the current.")


def timed(fn):
    t = time.perf_counter()
    out = fn()
    return time.perf_counter() - t, out


def stt(model):
    with open(WAV, "rb") as f:
        r = S.post(f"{BASE}/audio/transcriptions", headers=H, timeout=60,
                          files={"file": ("a.wav", f, "audio/wav")},
                          data={"model": model, "response_format": "json"})
    r.raise_for_status()
    return r.json().get("text", "")


def llm(extra):
    r = S.post(f"{BASE}/chat/completions", timeout=90,
                      headers={**H, "Content-Type": "application/json"},
                      json={"model": "gpt-5.4-mini", "max_completion_tokens": 700,
                            "messages": [{"role": "system", "content": SYSTEM},
                                         {"role": "user", "content": QUESTION}],
                            **extra})
    if r.status_code != 200:
        return None, r.text[:160]
    j = r.json()
    u = j.get("usage", {})
    rt = (u.get("completion_tokens_details") or {}).get("reasoning_tokens", "?")
    return j["choices"][0]["message"]["content"], f"{u.get('completion_tokens')} tok ({rt} reasoning)"


def tts(fmt):
    """Returns (seconds to first audio byte, seconds to last byte)."""
    t0 = time.perf_counter()
    with S.post(f"{BASE}/audio/speech", timeout=60, stream=True,
                       headers={**H, "Content-Type": "application/json"},
                       json={"model": "gpt-4o-mini-tts", "voice": "sage",
                             "input": REPLY, "response_format": fmt}) as r:
        r.raise_for_status()
        first = None
        for chunk in r.iter_content(4096):
            if chunk and first is None:
                first = time.perf_counter() - t0
    return first, time.perf_counter() - t0


def row(name, times, note=""):
    lo, hi = min(times), max(times)
    print(f"  {name:<34} {statistics.mean(times):5.2f}s  ({lo:.2f}-{hi:.2f})  {note}")


def main():
    print(f"input: {WAV.name}  runs per variant: {RUNS}\n")
    # Warm-up: DNS + TLS paid here, not by whichever variant happens to run
    # first. Variants are then interleaved so none is systematically unlucky.
    S.get(f"{BASE}/models", headers=H, timeout=30)

    print("STT (full request, upload + transcribe)")
    models = ("gpt-4o-transcribe", "gpt-4o-mini-transcribe")
    ts = {m: [] for m in models}
    texts = {}
    for _ in range(RUNS):
        for m in models:
            dt, texts[m] = timed(lambda: stt(m))
            ts[m].append(dt)
    for m in models:
        row(m, ts[m], f"-> {texts[m][:50]!r}")

    print("\nLLM gpt-5.4-mini (full response)")
    for name, extra in [("default", {}),
                        ("reasoning_effort=low", {"reasoning_effort": "low"}),
                        ("reasoning_effort=minimal", {"reasoning_effort": "minimal"}),
                        ("reasoning_effort=none", {"reasoning_effort": "none"})]:
        ts, note = [], ""
        for _ in range(RUNS):
            dt, (text, note) = timed(lambda: llm(extra))
            if text is None:
                break
            ts.append(dt)
        if ts:
            row(name, ts, note)
        else:
            print(f"  {name:<34} rejected: {note}")

    print("\nTTS gpt-4o-mini-tts  (first audio byte / complete)")
    for fmt in ("wav", "pcm"):
        firsts, totals = [], []
        for _ in range(RUNS):
            f, t = tts(fmt)
            firsts.append(f)
            totals.append(t)
        row(f"{fmt}: time to FIRST audio", firsts)
        row(f"{fmt}: time to COMPLETE", totals)

    print("\nLocal: ffmpeg mp3/wav -> S32_LE 48k stereo (current pipeline)")
    sample = ROOT / "scratch" / "assistant_response.mp3"
    if sample.exists():
        ts = []
        for _ in range(RUNS):
            dt, _ = timed(lambda: subprocess.run(
                ["ffmpeg", "-y", "-i", str(sample), "-f", "s32le", "-ar", "48000",
                 "-ac", "2", "/tmp/bench.raw"], capture_output=True, check=True))
            ts.append(dt)
        row("ffmpeg transcode", ts)


if __name__ == "__main__":
    main()
