"""Connectivity test for the OpenAI Realtime API — no audio, no cost.

Subsystem test per CLAUDE.md: prove the transport works before building the
streaming pipeline on top of it. Answers four questions independently of any
microphone, amplifier or application logic:

  1. Does the WebSocket connect and authenticate from this Pi?
  2. Is `gpt-realtime-2` accepted as a model?
  3. Is `sage` accepted as a voice?
  4. Does the server echo back a session confirming the config we asked for?

Deliberately sends no audio and requests no response, so it costs nothing
beyond session setup. Run:

    .venv/bin/python3 tests/test_realtime_connect.py
"""
import asyncio
import json
import os
import pathlib
import sys

import websockets
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env", override=True)

MODEL = os.environ.get("REALTIME_MODEL", "gpt-realtime-2.1")
VOICE = os.environ.get("REALTIME_VOICE", "sage")
SAMPLE_RATE = 24000  # Realtime API native rate for audio/pcm

URL = f"wss://api.openai.com/v1/realtime?model={MODEL}"


def _headers() -> dict:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("OPENAI_API_KEY is not set (checked .env and environment).")
    return {"Authorization": f"Bearer {key}"}


async def main() -> int:
    print(f"connecting  model={MODEL} voice={VOICE} rate={SAMPLE_RATE}")

    # websockets >=14 renamed extra_headers -> additional_headers. Support
    # both so this doesn't silently break on a version bump.
    kwargs = {"additional_headers": _headers()}
    try:
        conn = websockets.connect(URL, **kwargs)
    except TypeError:
        conn = websockets.connect(URL, extra_headers=_headers())

    async with conn as ws:
        print("connected, authenticated")

        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "type": "realtime",
                "output_modalities": ["audio"],
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                        "turn_detection": {"type": "semantic_vad"},
                    },
                    "output": {
                        "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                        "voice": VOICE,
                    },
                },
            },
        }))

        # Read a bounded number of events rather than looping forever, so a
        # server that never sends session.updated fails the test instead of
        # hanging it.
        for _ in range(10):
            try:
                event = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
            except asyncio.TimeoutError:
                print("FAIL timed out waiting for session.updated")
                return 1

            etype = event.get("type", "?")
            print(f"  <- {etype}")

            if etype == "error":
                err = event.get("error", {})
                print(f"FAIL server error: {err.get('message', event)}")
                return 1

            if etype == "session.updated":
                audio = event.get("session", {}).get("audio", {})
                got_voice = audio.get("output", {}).get("voice")
                got_rate = audio.get("input", {}).get("format", {}).get("rate")
                print()
                print(f"  model confirmed: {event['session'].get('model')}")
                print(f"  voice confirmed: {got_voice}")
                print(f"  input rate     : {got_rate}")
                print()
                if got_voice != VOICE:
                    print(f"FAIL asked for voice {VOICE!r}, server reports {got_voice!r}")
                    return 1
                print("PASS transport, auth, model and voice all accepted")
                return 0

        print("FAIL never received session.updated")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
