import os
import subprocess
import queue
import threading
import time
import requests
import json
import re
from dotenv import load_dotenv
from gpiozero import LED, Button
from gtts import gTTS

from common import audio_devices, vad_recorder
from common import wake_word

# Load environment variables. override=True because a stale `export
# GROQ_API_KEY=...` in ~/.bashrc silently shadowed .env for an entire debug
# session — load_dotenv() defaults to not overriding the real environment,
# so edits to .env looked like no-ops with nothing explaining why.
# .env is the single source of truth for config; the shell is not.
load_dotenv(override=True)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Runtime audio artifacts live in scratch/ (gitignored) rather than the repo root.
SCRATCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scratch")
os.makedirs(SCRATCH_DIR, exist_ok=True)
AUDIO_FILE = os.path.join(SCRATCH_DIR, "command.wav")
TTS_FILE_MP3 = os.path.join(SCRATCH_DIR, "response.mp3")
TTS_FILE_WAV = os.path.join(SCRATCH_DIR, "response.wav")

# Hardware is resolved by ALSA card name, not index — indices are not stable
# across reboots (see CLAUDE.md). Override via env if the card names change.
MIC_NAME_HINT = os.environ.get("MIC_NAME_HINT", "CORSAIR")
# hifiberry-dac replaced googlevoicehat-soundcard: that overlay claimed
# GPIO16 as its own amp-enable, conflicting with the HAT's AMP_EN on
# GPIO26. Switching overlays changes the ALSA card name, hence this
# default. Override with AMP_NAME_HINT if the card is named otherwise.
AMP_NAME_HINT = os.environ.get("AMP_NAME_HINT", "hifiberry")

# Bundled Hey Atlas model; WAKE_WORD can select an installed alternative.
WAKE_WORD = os.environ.get("WAKE_WORD", wake_word.DEFAULT_WAKE_WORD)
WAKE_WORD_ENABLED = os.environ.get("WAKE_WORD_ENABLED", "1").lower() not in ("0", "false")

# Recording now stops on detected silence instead of a fixed timer.
# Commands are short, so a tighter cap than the conversational assistant.
SILENCE_MS = 700
MAX_RECORD_SECONDS = 10

if not GROQ_API_KEY:
    print("❌ Error: GROQ_API_KEY is not set!")
    exit(1)

# Initialize Hardware Pins
led_17 = LED(17)                         # Physical Pin 11
button = Button(22, pull_up=True)       # Physical Pin 15 (Push-to-Talk)

# Map target devices to GPIO objects
# NOTE: both targets currently point at the same physical pin (led_17) —
# there is only one LED wired up, so "turn off monitor" will also turn off
# "desk_light" until a second GPIO/LED is wired. Flagging, not silently
# fixing, since it's a hardware wiring decision, not a software bug.
DEVICES = {
    "desk_light": led_17,
    "monitor": led_17,
}

# Trigger coordination: same pattern as voice_assistant.py — button and
# wake-word listeners run on separate threads and feed one queue. `busy`
# prevents the wake-word listener from fighting the VAD recorder over the
# mic while a command is being processed.
trigger_queue = queue.Queue(maxsize=1)
busy = threading.Event()


def _enqueue_trigger(source):
    """Claim the mic at enqueue time, not when the main loop gets round to it.

    The wake-word thread enqueues and then immediately loops back to reopen
    the mic. If `busy` were only set later by the main loop (after
    trigger_queue.get()), that reopen races the VAD recorder for the same
    device and one side loses with 'Device unavailable' — observed on
    hardware as ~5 failed PortAudio opens on every wake-word-triggered turn,
    while button-triggered turns stayed clean.

    Setting it here closes the window: the enqueuing thread sees busy already
    set on its very next check. Only claim it when the put actually
    succeeded — claiming for a dropped trigger would leave busy set with no
    turn in flight to clear it.
    """
    try:
        trigger_queue.put_nowait(source)
    except queue.Full:
        return
    busy.set()


def _watch_button():
    while True:
        button.wait_for_press()
        if not busy.is_set():
            _enqueue_trigger("button (GPIO 22)")
        button.wait_for_release()


def _watch_wake_word():
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


def verify_devices():
    """Fail fast and loud if the expected mic/amp aren't found."""
    mic_idx = audio_devices.find_card_index(MIC_NAME_HINT, "capture")
    amp_idx = audio_devices.find_card_index(AMP_NAME_HINT, "playback")
    print(f"🎙️  Mic resolved: card {mic_idx} (matched '{MIC_NAME_HINT}')")
    print(f"🔊 Amp resolved: card {amp_idx} (matched '{AMP_NAME_HINT}')")
    return audio_devices.amp_device(AMP_NAME_HINT)


def record_audio():
    """Captures audio via the resolved Corsair mic, stopping on silence."""
    print(f"\n🎤 Listening... (stops after ~{SILENCE_MS}ms of silence, {MAX_RECORD_SECONDS}s max)")
    got_speech = vad_recorder.record_until_silence(
        AUDIO_FILE,
        mic_name_hint=MIC_NAME_HINT,
        silence_ms=SILENCE_MS,
        max_seconds=MAX_RECORD_SECONDS,
    )
    print("⏹️ Recording finished." if got_speech else "⏹️ No speech detected before timeout.")
    return got_speech

def cloud_speech_to_text():
    """Transcribes audio using Groq Whisper API."""
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

    with open(AUDIO_FILE, "rb") as f:
        files = {"file": (AUDIO_FILE, f, "audio/wav")}
        data = {
            "model": "whisper-large-v3-turbo",
            "response_format": "json"
        }
        response = requests.post(url, headers=headers, files=files, data=data)

    if response.status_code == 200:
        return response.json().get("text", "")
    else:
        print("STT Error:", response.text)
        return ""

def cloud_llm_intent(user_text):
    """Parses intent via Groq LLM returning structured JSON."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = (
        "You are an AI assistant controlling a smart workstation. "
        "Convert the user command into a JSON object containing:\n"
        "1. 'commands': A list of objects with 'action' ('turn_on', 'turn_off') "
        "and 'target' ('desk_light', 'monitor').\n"
        "2. 'spoken_response': A short, natural Arabic confirmation phrase for the speaker "
        "(e.g., 'تم تشغيل الإضاءة' or 'تم إيقاف الشاشة').\n"
        "Respond strictly with raw JSON."
    )

    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        "response_format": {"type": "json_object"}
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print("LLM Error:", response.text)
        return "{}"

def speak_response(text, amp_device):
    """Generates Arabic TTS audio via the resolved I2S amp (S32_LE @ 44.1kHz)."""
    print(f"🔊 AI Speaking: '{text}'")
    try:
        tts = gTTS(text=text, lang='ar')
        tts.save(TTS_FILE_MP3)

        # Convert MP3 to 32-bit Little Endian (S32_LE) @ 44100 Hz required natively by MAX98357A
        subprocess.run(
            ["ffmpeg", "-y", "-i", TTS_FILE_MP3, "-f", "s32le", "-ar", "44100", "-ac", "2", TTS_FILE_WAV],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
        )

        # Play via the resolved hardware card (blocks until playback finishes).
        subprocess.run(
            ["aplay", "-D", amp_device, "-f", "S32_LE", "-r", "44100", "-c", "2", TTS_FILE_WAV],
            check=True,
        )
    except Exception as e:
        print("TTS Output Error:", e)

def execute_action(action, target):
    """Drives physical GPIO pins."""
    device = DEVICES.get(target)

    if not device:
        print(f"⚠️ Target device '{target}' is not assigned to a GPIO pin.")
        return

    if action == "turn_on":
        device.on()
        print(f"🔌 [GPIO 17 HIGH] LED Turned ON")
    elif action == "turn_off":
        device.off()
        print(f"🔌 [GPIO 17 LOW] LED Turned OFF")

if __name__ == "__main__":
    print("🚀 Push-to-Talk Smart Workstation Ready.")
    print("🔘 Press the physical button on GPIO 22 to speak. Press Ctrl+C to exit.")

    amp_device = verify_devices()

    threading.Thread(target=_watch_button, daemon=True).start()
    if WAKE_WORD_ENABLED:
        threading.Thread(target=_watch_wake_word, daemon=True).start()
        print(f"👂 Wake word '{WAKE_WORD}' active (openWakeWord, runs on-device).")
    else:
        print("👂 Wake word disabled (WAKE_WORD_ENABLED=0) — button only.")

    try:
        while True:
            source = trigger_queue.get()
            busy.set()
            print(f"\n🎯 Triggered by {source}")
            try:
                if not record_audio():
                    print("💤 No voice detected. Ready for next trigger...")
                    continue

                transcript = cloud_speech_to_text()
                print(f"🗣️ Transcribed Text: '{transcript}'")

                cleaned_transcript = re.sub(r'[\.\s]', '', transcript)

                if cleaned_transcript:
                    raw_response = cloud_llm_intent(transcript)
                    print(f"⚙️ Parsed Action JSON: {raw_response}\n")

                    try:
                        data = json.loads(raw_response)
                        commands = data.get("commands", [])
                        spoken_text = data.get("spoken_response", "")

                        if isinstance(commands, dict):
                            commands = [commands]

                        for cmd in commands:
                            action = cmd.get("action")
                            target = cmd.get("target")
                            print(f"🎯 Action: {action} | Target: {target}")
                            execute_action(action, target)

                        if spoken_text and commands:
                            speak_response(spoken_text, amp_device)

                    except Exception as e:
                        print("Failed to parse JSON execution:", e)
                else:
                    print("💤 No voice detected. Ready for next trigger...")
            finally:
                busy.clear()

    except KeyboardInterrupt:
        print("\n🛑 Workstation daemon stopped safely.")
