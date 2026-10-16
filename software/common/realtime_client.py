"""OpenAI Realtime API session over WebSocket.

Architectural note — this is not a drop-in swap for the Groq pipeline.
The old path made four sequential HTTP requests per turn (record a file,
upload for transcription, ask the LLM, synthesise speech). This opens one
persistent socket and streams audio both ways: speech-to-speech happens
server-side, so there is no separate STT, LLM or TTS step to orchestrate.

Consequences worth knowing:
  - Turn detection moves server-side (`semantic_vad`), so webrtcvad is not
    used during a session. The local wake word still gates whether a session
    opens at all, which is what stops the mic streaming to OpenAI while idle.
  - Audio is billed per token in both directions, so session lifetime
    matters far more than request count did. `idle_timeout_s` closes a
    session that has gone quiet.
  - Barge-in becomes possible: the server reports when the user starts
    speaking, and playback can be cut mid-sentence.

Event names follow the GA schema (nested `audio.input` / `audio.output`),
not the older flat preview fields.
"""
import base64
import json

import websockets

WS_URL = "wss://api.openai.com/v1/realtime"
SAMPLE_RATE = 24000  # Realtime API native rate for audio/pcm


class RealtimeSession:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-realtime-2.1",
        voice: str = "sage",
        instructions: str | None = None,
    ):
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._instructions = instructions
        self._ws = None

    async def __aenter__(self):
        url = f"{WS_URL}?model={self._model}"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        # websockets >=14 renamed extra_headers -> additional_headers.
        try:
            self._ws = await websockets.connect(url, additional_headers=headers)
        except TypeError:
            self._ws = await websockets.connect(url, extra_headers=headers)
        await self._configure()
        return self

    async def __aexit__(self, *exc):
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def _configure(self) -> None:
        session: dict = {
            "type": "realtime",
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                    # Server-side turn detection. semantic_vad judges whether
                    # the user has actually finished a thought rather than
                    # just paused, which suits spoken questions better than a
                    # fixed silence threshold.
                    "turn_detection": {"type": "semantic_vad"},
                    # Off by default, and worth the small extra cost: without
                    # it there is no record of what the server actually heard,
                    # so "the mic sent silence" and "the model chose not to
                    # answer" look identical from the console.
                    "transcription": {"model": "whisper-1"},
                },
                "output": {
                    "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                    "voice": self._voice,
                },
            },
        }
        if self._instructions:
            session["instructions"] = self._instructions
        await self._send({"type": "session.update", "session": session})

    async def _send(self, payload: dict) -> None:
        await self._ws.send(json.dumps(payload))

    async def send_audio(self, pcm16_mono_24k: bytes) -> None:
        """Append a chunk of mic audio to the server's input buffer."""
        await self._send({
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(pcm16_mono_24k).decode("ascii"),
        })

    async def cancel_response(self) -> None:
        """Stop the model mid-utterance (barge-in)."""
        await self._send({"type": "response.cancel"})

    async def events(self):
        """Yield decoded server events until the socket closes."""
        async for raw in self._ws:
            yield json.loads(raw)
