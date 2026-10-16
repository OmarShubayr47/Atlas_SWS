"""Speech-to-speech assistant on the OpenAI Realtime API.

Runs alongside voice_assistant.py rather than replacing it — that one is the
tested, working Groq-era pipeline and stays as a fallback until this proves
itself on hardware.

Shape of a turn:

    idle  -> local wake word (openWakeWord, on-device) or PTT button
          -> open a Realtime WebSocket session
          -> stream mic audio up / stream model audio down, continuously,
             with the server deciding when each turn ends
          -> session closes after `idle_timeout_s` of nothing happening
          -> back to idle

The local wake word is deliberately kept rather than letting the server's VAD
listen from idle: it means microphone audio only leaves the Pi after the wake
word fires. That matters for privacy, and for cost — Realtime bills per audio
token in both directions, so an always-open session is an always-running
meter.
"""
import asyncio
import base64
import os
import queue
import threading
import time

from dotenv import load_dotenv
from gpiozero import Button

from common import audio_devices, audio_out, realtime_client, wake_word
from common.mic_stream import MicStream

load_dotenv(override=True)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("REALTIME_MODEL", "gpt-realtime-2.1")
VOICE = os.environ.get("REALTIME_VOICE", "sage")

MIC_NAME_HINT = os.environ.get("MIC_NAME_HINT", "CORSAIR")
# hifiberry-dac replaced googlevoicehat-soundcard: that overlay claimed
# GPIO16 as its own amp-enable, conflicting with the HAT's AMP_EN on
# GPIO26. Switching overlays changes the ALSA card name, hence this
# default. Override with AMP_NAME_HINT if the card is named otherwise.
AMP_NAME_HINT = os.environ.get("AMP_NAME_HINT", "hifiberry")

WAKE_WORD = os.environ.get("WAKE_WORD", wake_word.DEFAULT_WAKE_WORD)
WAKE_WORD_ENABLED = os.environ.get("WAKE_WORD_ENABLED", "1").lower() not in ("0", "false")

# Close a session that has gone quiet. Without this the socket stays open
# (and billable) after the user wanders off.
IDLE_TIMEOUT_S = float(os.environ.get("REALTIME_IDLE_TIMEOUT", "20"))
MIC_CHUNK_MS = 40

# REALTIME_DEBUG=1 traces where a session stalls. Three isolation tests
# (sustained capture; capture+network; concurrent opens) each failed to
# reproduce the USB disconnect seen in real sessions, so the remaining
# unknown is inside this file's orchestration. Without a trace, a stalled
# session and a silent model look identical from the console.
DEBUG = os.environ.get("REALTIME_DEBUG", "0").lower() not in ("0", "false")


def _dbg(msg: str) -> None:
    if DEBUG:
        print(f"   [dbg {time.strftime('%H:%M:%S')}] {msg}", flush=True)


INSTRUCTIONS = (
    "You are a helpful, witty, concise AI assistant built into a Raspberry Pi "
    "workstation. Keep replies short and natural for speech. If the user "
    "speaks Arabic, reply in natural spoken Arabic; if English, reply in English."
)

if not OPENAI_API_KEY:
    raise SystemExit("OPENAI_API_KEY is not set (checked .env and environment).")

button = Button(22, pull_up=True)

# Same trigger-coordination pattern as voice_assistant.py: button and
# wake-word watchers are threads feeding one single-slot queue, and `busy`
# marks that the mic is spoken for. The enqueuing thread claims busy itself
# — if the main loop set it after dequeuing, the wake-word thread would loop
# round and reopen the mic in the gap, which collides with whoever opens it
# next (observed on hardware as repeated 'Device unavailable').
trigger_queue: queue.Queue = queue.Queue(maxsize=1)
busy = threading.Event()


def _enqueue_trigger(source: str) -> None:
    try:
        trigger_queue.put_nowait(source)
    except queue.Full:
        return
    busy.set()


def _watch_button() -> None:
    while True:
        button.wait_for_press()
        if not busy.is_set():
            _enqueue_trigger("button (GPIO 22)")
        button.wait_for_release()


def _watch_wake_word() -> None:
    while True:
        if busy.is_set():
            time.sleep(0.2)
            continue
        try:
            detected = wake_word.listen_for_wake_word(
                wake_word=WAKE_WORD, mic_name_hint=MIC_NAME_HINT, stop_event=busy
            )
        except Exception as e:
            print(f"⚠️ Wake word listener error: {e}")
            time.sleep(2)
            continue
        if detected and not busy.is_set():
            _enqueue_trigger(f"wake word ('{WAKE_WORD}')")


def verify_devices() -> str:
    mic_idx = audio_devices.find_card_index(MIC_NAME_HINT, "capture")
    amp_idx = audio_devices.find_card_index(AMP_NAME_HINT, "playback")
    print(f"🎙️  Mic resolved: card {mic_idx} (matched '{MIC_NAME_HINT}')")
    print(f"🔊 Amp resolved: card {amp_idx} (matched '{AMP_NAME_HINT}')")
    return audio_devices.amp_device(AMP_NAME_HINT)


def _mic_reader(mic: MicStream, out_queue: "queue.Queue[bytes | None]",
                stop_flag: threading.Event) -> None:
    """Read the mic in a dedicated thread and hand chunks off via a queue.

    Deliberately NOT asyncio.to_thread-per-read. Two problems with that:

    1. Network latency got inside the capture loop. Each iteration read 40ms
       of audio then awaited a WebSocket send before reading again, so a slow
       send starved the USB isochronous stream. On this hardware that
       produced `xhci-hcd: WARN: buffer overrun event ... on endpoint`,
       followed by the hub disabling the port and the mic vanishing from the
       bus entirely. Reading continuously in its own thread means the socket
       can stall without the capture stream ever missing a deadline.

    2. A to_thread call cannot be cancelled. Cancelling the task left the
       worker still blocked inside PortAudio's read while the cleanup path
       called mic.close() underneath it — which is what produced
       `alsa_snd_pcm_drop(...) failed` on shutdown. Here the thread owns the
       reads, is told to stop by a flag, and is joined before the mic closes.

    A bounded queue matters: if the sender falls behind, drop the oldest
    audio rather than growing without limit. Stale microphone audio has no
    value once it is seconds late.
    """
    read_count = 0
    try:
        _dbg("mic reader thread started")
        while not stop_flag.is_set():
            chunk = mic.read_ms(MIC_CHUNK_MS)
            read_count += 1
            if read_count == 1:
                _dbg("mic reader: FIRST chunk read OK")
            elif read_count % 50 == 0:
                _dbg(f"mic reader: {read_count} chunks (~{read_count*MIC_CHUNK_MS/1000:.0f}s)")
            try:
                out_queue.put_nowait(chunk)
            except queue.Full:
                try:
                    out_queue.get_nowait()      # drop oldest
                    out_queue.put_nowait(chunk)
                except queue.Empty:
                    pass
    except Exception as e:
        print(f"\u26a0\ufe0f Mic reader stopped after {read_count} chunks: "
              f"{type(e).__name__}: {e}")
    finally:
        _dbg(f"mic reader exiting after {read_count} chunks")
        out_queue.put(None)   # sentinel: unblock the sender


async def _pump_mic(session, audio_queue: "queue.Queue[bytes | None]",
                    stop: asyncio.Event, sent: list) -> None:
    """Drain captured audio to the server. Never touches the mic itself."""
    while not stop.is_set():
        chunk = await asyncio.to_thread(audio_queue.get)
        if chunk is None or stop.is_set():
            _dbg("sender: stopping")
            break
        await session.send_audio(chunk)
        sent[0] += 1
        if sent[0] == 1:
            _dbg("sender: FIRST chunk sent to server OK")
        elif sent[0] % 50 == 0:
            _dbg(f"sender: {sent[0]} chunks uploaded")


async def _pump_events(session, player: audio_out.StreamingPlayer,
                       stop: asyncio.Event, activity: list) -> None:
    """Consume server events: play audio, print transcripts, handle barge-in."""
    async for event in session.events():
        if stop.is_set():
            break
        etype = event.get("type", "")
        activity[0] = time.monotonic()
        _dbg(f"event <- {etype}")

        if etype == "response.output_audio.delta":
            player.write(base64.b64decode(event["delta"]))

        elif etype == "input_audio_buffer.speech_started":
            # Barge-in: the user started talking over the model. Drop what is
            # queued for playback and tell the server to stop generating,
            # otherwise it keeps talking into the interruption.
            player.stop()
            await session.cancel_response()
            print("\n🎤 (listening)")

        elif etype == "response.output_audio_transcript.done":
            print(f"🔊 Assistant: {event.get('transcript', '').strip()}")

        elif etype == "conversation.item.input_audio_transcription.completed":
            print(f"🗣️  You: {event.get('transcript', '').strip()}")

        elif etype == "error":
            print(f"⚠️ Server error: {event.get('error', {}).get('message', event)}")

        elif etype == "response.done":
            player.finish()


async def _watch_idle(stop: asyncio.Event, activity: list) -> None:
    while not stop.is_set():
        await asyncio.sleep(1)
        if time.monotonic() - activity[0] > IDLE_TIMEOUT_S:
            print(f"\n💤 Idle {IDLE_TIMEOUT_S:.0f}s — closing session.")
            stop.set()


async def run_session(amp_device: str) -> None:
    player = audio_out.StreamingPlayer(amp_device)
    mic = MicStream(MIC_NAME_HINT, target_rate=realtime_client.SAMPLE_RATE)
    stop = asyncio.Event()
    activity = [time.monotonic()]  # list so the coroutines share one cell
    sent = [0]

    # ~2s of audio at MIC_CHUNK_MS. Enough to ride out a network hiccup,
    # small enough that we notice rather than silently accumulating lag.
    audio_queue: queue.Queue = queue.Queue(maxsize=int(2000 / MIC_CHUNK_MS))
    reader_stop = threading.Event()
    reader = threading.Thread(
        target=_mic_reader, args=(mic, audio_queue, reader_stop), daemon=True
    )

    try:
        async with realtime_client.RealtimeSession(
            api_key=OPENAI_API_KEY, model=MODEL, voice=VOICE,
            instructions=INSTRUCTIONS,
        ) as session:
            print(f"🔗 Session open ({MODEL}, voice '{VOICE}') — speak now.")
            reader.start()
            tasks = [
                asyncio.create_task(_pump_mic(session, audio_queue, stop, sent)),
                asyncio.create_task(_pump_events(session, player, stop, activity)),
                asyncio.create_task(_watch_idle(stop, activity)),
            ]
            # Stop on the first task to finish, not only on `stop` — a task
            # that dies on an exception used to leave the session sitting
            # there doing nothing until the idle timeout, with the exception
            # never retrieved and never printed. Silent failure is worse than
            # a crash: it looks identical to "the model had nothing to say".
            done, pending = await asyncio.wait(
                [*tasks, asyncio.create_task(stop.wait())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            stop.set()
            for t in pending:
                t.cancel()
            for t in done:
                exc = t.exception() if not t.cancelled() else None
                if exc is not None:
                    print(f"⚠️ {type(exc).__name__}: {exc}")
            await asyncio.gather(*pending, return_exceptions=True)
    finally:
        # Order matters: stop the reader and wait for it to actually leave
        # PortAudio before closing the mic. Closing a stream while another
        # thread is blocked reading it is what wedged the device previously.
        reader_stop.set()
        if reader.is_alive():
            reader.join(timeout=2)
            if reader.is_alive():
                print("⚠️ Mic reader did not stop; leaving stream open to avoid a wedged device.")
                player.stop()
                return
        player.stop()
        mic.close()


async def main() -> None:
    print("=" * 50)
    print("🤖 Realtime Voice Assistant")
    print(f"   model: {MODEL}   voice: {VOICE}")
    print("🔘 Press the button on GPIO 22, or say the wake word.")
    print("=" * 50)

    amp_device = verify_devices()

    threading.Thread(target=_watch_button, daemon=True).start()
    if WAKE_WORD_ENABLED:
        threading.Thread(target=_watch_wake_word, daemon=True).start()
        print(f"👂 Wake word '{WAKE_WORD}' active (on-device; audio only leaves the Pi after it fires).")
    else:
        print("👂 Wake word disabled (WAKE_WORD_ENABLED=0) — button only.")

    while True:
        source = await asyncio.to_thread(trigger_queue.get)
        print(f"\n🎯 Triggered by {source}")
        try:
            await run_session(amp_device)
        except Exception as e:
            print(f"⚠️ Session error: {type(e).__name__}: {e}")
        finally:
            busy.clear()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Realtime assistant closed.")
