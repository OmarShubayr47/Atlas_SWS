import os
import subprocess
import queue
import sys
import threading
import time
from contextlib import nullcontext
from datetime import datetime
import requests
from dotenv import load_dotenv
from gpiozero import Button

# Load environment variables. override=True because a stale `export
# GROQ_API_KEY=...` in ~/.bashrc silently shadowed .env for an entire debug
# session — load_dotenv() defaults to not overriding the real environment,
# so edits to .env looked like no-ops with nothing explaining why.
# .env is the single source of truth for config; the shell is not.
# Must run BEFORE the project imports below: common/ modules read their
# settings (AMP_EN_PIN, VOLUME_MAX, UI_PORT, ...) at import time, so loading
# .env afterwards would silently ignore those keys.
load_dotenv(override=True)

from common import amp_enable, audio_devices, ui_events, vad_recorder, volume  # noqa: E402
from common import encoder, keepalive_output, wake_word  # noqa: E402
from common import liveness, sd_notify, speech_volume, status_led  # noqa: E402
from tools import registry  # noqa: E402

# DNS: this network's resolvers drop one of the parallel A/AAAA queries glibc
# sends by default, so the FIRST lookup in every process stalls for the full
# 5 s resolver timeout (measured 5.04-5.17 s; each query alone 0.01 s).
# single-request-reopen sends them one at a time: first lookup 0.02 s.
# glibc reads RES_OPTIONS at its first lookup, so this must run before any
# network call. setdefault: a value from .env or the shell still wins.
os.environ.setdefault("RES_OPTIONS", "single-request-reopen")

# One keep-alive session for all API calls: STT, LLM and TTS reuse a single
# TCP+TLS connection instead of each paying a fresh handshake.
HTTP = requests.Session()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BASE = "https://api.openai.com/v1"

# Models are env-overridable so they can be swapped without editing code —
# the hosted catalogue changes faster than this repo does. Defaults verified
# present on this account's /v1/models listing, not assumed.
# mini-transcribe measured ~1.0 s vs 4.7 s (1.5-7.9 s) for gpt-4o-transcribe on
# the same recording (tests/latency_bench.py) — the single biggest latency
# win. Arabic accuracy still to be confirmed in real use; if it is worse, set
# STT_MODEL=gpt-4o-transcribe in .env to switch back.
STT_MODEL = os.environ.get("STT_MODEL", "gpt-4o-mini-transcribe")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gpt-5.4-mini")
TTS_MODEL = os.environ.get("TTS_MODEL", "gpt-4o-mini-tts")
# Voice confirmed accepted by the API (tests/test_realtime_connect.py).
TTS_VOICE = os.environ.get("TTS_VOICE", "sage")
# Healthy speech requests answer in 0.6-0.9 s; some hang with no answer at all
# (2026-10-12). Give up on one after this many seconds and retry (_open_tts_stream).
TTS_FIRST_BYTE_TIMEOUT = float(os.environ.get("TTS_FIRST_BYTE_TIMEOUT", "8"))
TTS_ATTEMPTS = 3
# Measured 1.50 s vs 1.72 s default; the model spent 0 reasoning tokens on a
# plain question either way, so this is a small trim, not a big win. Accepted
# values for this model: none / low / medium ('minimal' is rejected).
# Must be 'none' while tools are sent: the API now rejects function tools
# combined with any other reasoning_effort for gpt-5.4-mini on
# /v1/chat/completions (400 invalid_request_error, observed 2026-09-22).
REASONING_EFFORT = os.environ.get("REASONING_EFFORT", "none")

# Runtime audio artifacts live in scratch/ (gitignored) rather than the repo root.
SCRATCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scratch")
os.makedirs(SCRATCH_DIR, exist_ok=True)
AUDIO_FILE = os.path.join(SCRATCH_DIR, "assistant_input.wav")

# Hardware is resolved by ALSA card name, not index — indices are not stable
# across reboots (see CLAUDE.md). Override via env if the card names change.
MIC_NAME_HINT = os.environ.get("MIC_NAME_HINT", "CORSAIR")
# hifiberry-dac replaced googlevoicehat-soundcard: that overlay claimed
# GPIO16 as its own amp-enable, conflicting with the HAT's AMP_EN on
# GPIO26. Switching overlays changes the ALSA card name, hence this
# default. Override with AMP_NAME_HINT if the card is named otherwise.
AMP_NAME_HINT = os.environ.get("AMP_NAME_HINT", "hifiberry")
# Optional ALSA playback target that replaces the amp for speech, e.g.
# "plug:'hdmi:CARD=vc4hdmi0,DEV=0'" to evaluate the projector's speakers.
# The HDMI card only takes IEC958 frames, which plughw can't produce; the
# hdmi: config does that, and plug: converts 24 kHz mono to what it accepts.
# The inner quotes are required: unquoted, ALSA splits plug:'s argument at
# the comma and the open fails with "No such file or directory" (tested
# 2026-09-22). vc4hdmi0 = HDMI-A-1, the port the projector is on (checked
# via /sys/class/drm/*/status).
# Unset (the default) keeps the I2S amp.
PLAYBACK_PCM = os.environ.get("PLAYBACK_PCM", "").strip()
# Set at startup when PLAYBACK_PCM is used: one stream kept open for the whole
# session, because the projector drops the first seconds of every new HDMI
# audio stream (see common/keepalive_output.py). None = per-reply aplay.
_keepalive = None
# Digital gain for speech on the PLAYBACK_PCM path (soft-limited). TTS peaks
# measured -15.4 dBFS, so +12 dB brings a typical reply to ~-3 dBFS: louder
# with no clipping. Amp path is unaffected (its level is the ALSA Master).
SPEECH_GAIN_DB = float(os.environ.get("SPEECH_GAIN_DB", "12"))
# The encoder's level, applied on top of SPEECH_GAIN_DB to whichever output
# is active (common/speech_volume.py explains why not the ALSA mixer). Set
# at startup.
_volume = None

# Bundled Hey Atlas model; WAKE_WORD can select an installed alternative.
WAKE_WORD = os.environ.get("WAKE_WORD", wake_word.DEFAULT_WAKE_WORD)
WAKE_WORD_ENABLED = os.environ.get("WAKE_WORD_ENABLED", "1").lower() not in ("0", "false")

# Recording now stops on detected silence instead of a fixed timer.
SILENCE_MS = 800
MAX_RECORD_SECONDS = 20

# Messages kept in conversation_history, including the system prompt.
# Deliberately larger than the old limit of 11: with tool calling, a single
# exchange can be four messages (user, assistant tool_calls, tool result,
# assistant answer) rather than two, so the old value held barely two turns
# once tools were in play. Every message here is re-sent on every request,
# so this is a direct cost/memory trade — raise it for a longer memory,
# lower it for cheaper turns.
MAX_HISTORY = int(os.environ.get("MAX_HISTORY", "25"))

# Bound on consecutive tool-call rounds within ONE user turn. The model can
# legitimately chain calls (find a file, then read it, then search it), but
# without a ceiling a model that keeps calling tools would spin while the
# user waits in silence with no way to tell whether it is working or stuck.
MAX_TOOL_ROUNDS = int(os.environ.get("MAX_TOOL_ROUNDS", "5"))

# Physical controls. PTT on GPIO22 (pin 15) as before. The encoder is the
# volume knob: turn = level, push = mute (GPIO5/6/13, see common/encoder.py).
PTT_PIN = int(os.environ.get("PTT_PIN", "22"))
# A press within this long of the press that started a turn is ignored, so
# one bouncy press can never both start a turn and immediately stop it.
PTT_GUARD_S = 0.5
ENCODER_ENABLED = os.environ.get("ENCODER_ENABLED", "1").lower() not in ("0", "false", "")
# The Pi's internal pull-ups on the encoder's A/B lines. Both encoders in this
# project have external pull-ups (KY-040: 10k on the module; HAT: 1k), so
# this only parallels them — but it also means an UNPLUGGED encoder reads as
# "at rest" instead of floating, which would otherwise turn electrical noise
# into phantom volume clicks on an always-on machine.
ENC_PULL_UP = os.environ.get("ENC_PULL_UP", "1").lower() not in ("0", "false", "")

# A microphone that stays unopenable is not coming back inside this process:
# PortAudio enumerates devices once, when it starts, and this process keeps
# one PortAudio instance for its whole life (see common/mic_stream.py). So
# after this many failures in a row the assistant exits on purpose; systemd
# starts a fresh one, which waits for the mic to reappear.
MIC_FAILURES_BEFORE_EXIT = 3

if not OPENAI_API_KEY:
    print("❌ Error: OPENAI_API_KEY is not set!")
    exit(1)

# Push-to-Talk button on GPIO 22 (physical pin 15). 5 ms debounce, the
# project's convention (CLAUDE.md), same as the restart button.
button = Button(PTT_PIN, pull_up=True, bounce_time=0.005)

# Conversation History Memory
SYSTEM_PROMPT = (
    "You are a helpful, witty, and concise AI voice assistant on a Raspberry Pi workstation. "
    "Respond naturally in brief sentences suitable for text-to-speech output. "
    "Your reply is spoken aloud, never displayed: use plain sentences only. "
    "No markdown, no bullet lists, no backticks, no headings: say file and commit "
    "names plainly rather than in code punctuation, and turn lists into sentences. "
    "If the user speaks Arabic, reply in natural spoken Arabic. "
    "If they speak English, reply in natural spoken English. "
    # Capabilities (T-004 phase 3). Kept in the prompt as well as the tool
    # descriptions so the model knows the screen exists and what it may do.
    "The workstation has a projector. You can show files on it with open_file, "
    "zoom, scroll or turn pages with control_view, close them with close_view, "
    "list the user's own files with show_workspace, save new notes or text "
    "files with create_note and create_text_file, and draw circuit schematics "
    "from templates with create_schematic, then change them with "
    "modify_schematic. New files go into the user's "
    "workspace and appear on the projector automatically. You can never delete, "
    "replace or run files. After showing or creating a file, confirm it in one "
    "short sentence instead of reading the content aloud. After drawing or "
    "changing a schematic, say its key computed values and every assumption "
    "from the tool result, in one or two short sentences. Never state a "
    "measured or component value that a tool did not give you."
)
conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]

# Trigger coordination: button and wake-word listeners run on separate
# threads and both feed the same queue. `busy` is cleared/set so the two
# listeners don't both try to open the mic while a turn is being processed
# (button watching doesn't touch audio hardware, wake-word listening does).
trigger_queue = queue.Queue(maxsize=1)
busy = threading.Event()

# Turn control from the PTT button while a turn is running:
#   _stop_listening  "I'm done talking" — end the recording now
#   _cancel          "stop" — abandon the turn and silence the reply
_stop_listening = threading.Event()
_cancel = threading.Event()
_stage = "idle"            # what the assistant is doing, for the button
_turn_started_at = 0.0     # monotonic time of the last trigger
_current_player = None     # per-reply aplay on the amp path, for cancel

# Health: watched by the liveness thread (systemd watchdog + UI heartbeat).
LIVENESS = liveness.Liveness()
_mic_failures = 0
_mic_lock = threading.Lock()
_fatal = threading.Event()
_fatal_reason = ""


def _set_state(state, detail=None):
    """One place for state changes: the projected UI and the button's LED.

    Fire-and-forget on both: if the UI server is not running the event is
    dropped, and a missing LED is a no-op.
    """
    global _stage
    _stage = state
    status_led.show(state)
    if detail is None:
        ui_events.publish("state", state=state)
    else:
        ui_events.publish("state", state=state, detail=detail)


def _mic_failed(error):
    """Count a failure to open/read the mic; give up after several in a row."""
    global _mic_failures, _fatal_reason
    with _mic_lock:
        _mic_failures += 1
        count = _mic_failures
    if count >= MIC_FAILURES_BEFORE_EXIT and not _fatal.is_set():
        _fatal_reason = (f"microphone failed {count} times in a row "
                         f"(last: {type(error).__name__}: {error})")
        _fatal.set()


def _mic_ok():
    """The mic delivered audio. Called per chunk, so: one store, no lock."""
    global _mic_failures
    _mic_failures = 0


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
    global _turn_started_at
    try:
        trigger_queue.put_nowait(source)
    except queue.Full:
        return
    _turn_started_at = time.monotonic()
    busy.set()


def _interrupt():
    """PTT pressed while a turn is running.

    While listening it means "I'm done talking": end the recording and answer
    what was said. Any later — thinking or speaking — it means "stop": the
    reply is abandoned and silenced at once, which is the only way to stop a
    long answer without waiting for it.
    """
    if _stage == "listening":
        print("🔘 Button: finish listening")
        _stop_listening.set()
        return
    print("🔘 Button: stop")
    _cancel.set()
    if _keepalive is not None:
        _keepalive.cancel()
    player = _current_player
    if player is not None and player.poll() is None:
        player.kill()
    _set_state("idle", "Stopped")


def _watch_button():
    while True:
        button.wait_for_press()
        if not busy.is_set():
            _enqueue_trigger(f"button (GPIO {PTT_PIN})")
        elif time.monotonic() - _turn_started_at > PTT_GUARD_S:
            _interrupt()
        button.wait_for_release()


def _wake_word_chunk():
    LIVENESS.wake_word_progress()
    _mic_ok()


def _watch_wake_word():
    while True:
        LIVENESS.wake_word_progress()
        if busy.is_set() or _fatal.is_set():
            time.sleep(0.2)
            continue
        try:
            detected = wake_word.listen_for_wake_word(
                wake_word=WAKE_WORD, mic_name_hint=MIC_NAME_HINT, stop_event=busy,
                on_progress=_wake_word_chunk,
            )
        except Exception as e:
            print(f"⚠️ Wake word listener error: {e}")
            _mic_failed(e)
            time.sleep(2)
            continue
        if detected and not busy.is_set():
            _enqueue_trigger(f"wake word ('{WAKE_WORD}')")


def wait_for_mic():
    """Return the mic's ALSA card index, waiting for it if it is not there.

    The old fail-fast check made a boot without the mic (or a mic that
    enumerates late) a crash; two detached launches on 2026-09-27 failed
    exactly here with no card listed. Under systemd that would become a
    restart every few seconds with a blank screen. Instead: say so on the
    projector, keep checking, and log how long the wait took — which is also
    evidence about that unexplained 2026-09-27 failure.

    Uses the ALSA listing (arecord -l), not PyAudio: PortAudio must not start
    before the mic exists, because it never re-enumerates afterwards.
    """
    started = time.monotonic()
    announced = False
    last_log = None
    while True:
        try:
            idx = audio_devices.find_card_index(MIC_NAME_HINT, "capture")
        except (RuntimeError, OSError, subprocess.SubprocessError) as e:
            if not announced:
                _set_state("error", "Microphone not found — check the USB mic")
                announced = True
            now = time.monotonic()
            if last_log is None or now - last_log >= 60:
                print(f"⏳ Waiting for the microphone: {e}", flush=True)
                last_log = now
            time.sleep(3)
            continue
        if announced:
            print(f"🎙️  Microphone appeared after {time.monotonic() - started:.0f} s.")
        return idx


def verify_devices():
    """Resolve the mic (waiting for it) and the amp. Returns the amp device,
    or None when speech goes to PLAYBACK_PCM and no amp is present."""
    mic_idx = wait_for_mic()
    print(f"🎙️  Mic resolved: card {mic_idx} (matched '{MIC_NAME_HINT}')")
    try:
        amp_idx = audio_devices.find_card_index(AMP_NAME_HINT, "playback")
        amp = audio_devices.amp_device(AMP_NAME_HINT)
        print(f"🔊 Amp resolved: card {amp_idx} (matched '{AMP_NAME_HINT}')")
    except (RuntimeError, OSError, subprocess.SubprocessError) as e:
        if not PLAYBACK_PCM:
            raise
        print(f"⚠️  Amp not found ({e}); not needed while speech goes to PLAYBACK_PCM.")
        amp = None
    if PLAYBACK_PCM:
        print(f"🔊 Speech output overridden: {PLAYBACK_PCM} (PLAYBACK_PCM)")
    if amp:
        _cap_volume()
    return amp


def _cap_volume():
    """Pull the amp's Master level down to the safe maximum if it is above it.

    The driver's default is 255 (+18.85 dB), and alsa-restore reloads whatever
    was last saved at every boot, so a reset or a fresh image quietly comes
    back in digital boost, which clips on loud speech (see volume.py). Found
    at 255 on 2026-09-22. Only lowers, never raises: a level the user turned
    down stays down. VOLUME_MAX in .env moves the ceiling deliberately.
    A mixer failure is a warning, not a crash, since speech still works.
    """
    try:
        raw = volume.get_raw()
        if raw > volume.DEFAULT_MAX:
            volume.set_raw(volume.DEFAULT_MAX)
            print(f"🔉 Volume was raw {raw} (digital boost); capped to "
                  f"{volume.DEFAULT_MAX} (~0 dB). Raise VOLUME_MAX to allow more.")
    except Exception as e:  # noqa: BLE001 - volume is not worth failing startup
        print(f"⚠️  Could not check volume: {type(e).__name__}: {e}")


def _start_encoder(vol):
    """The volume knob: turn for level, push for mute. Optional hardware."""
    if not ENCODER_ENABLED:
        print("🎛️  Volume encoder disabled (ENCODER_ENABLED=0).")
        return None
    try:
        # Callbacks run on the GPIO thread and must be fast (encoder.py):
        # step() and toggle_mute() only do arithmetic and a non-blocking
        # publish; saving the level happens on another thread.
        knob = encoder.RotaryEncoder(pull_up=ENC_PULL_UP, on_rotate=vol.step,
                                     on_press=vol.toggle_mute)
    except Exception as e:  # noqa: BLE001 - a knob is not worth failing startup
        print(f"⚠️  Volume encoder unavailable ({type(e).__name__}: {e}); "
              "continuing without it.")
        return None
    print(f"🎛️  Volume encoder on GPIO{encoder.DEFAULT_CLK}/{encoder.DEFAULT_DT}, "
          f"push on GPIO{encoder.DEFAULT_SW} = mute; {vol.describe()}")
    return knob


def record_audio():
    """Captures audio via the resolved Corsair mic, stopping on silence."""
    print(f"\n🎤 Listening... (stops after ~{SILENCE_MS}ms of silence, {MAX_RECORD_SECONDS}s max)")
    got_speech = vad_recorder.record_until_silence(
        AUDIO_FILE,
        mic_name_hint=MIC_NAME_HINT,
        silence_ms=SILENCE_MS,
        max_seconds=MAX_RECORD_SECONDS,
        stop_event=_stop_listening,
        on_progress=LIVENESS.turn_progress,
    )
    print("⏹️ Recording finished." if got_speech else "⏹️ No speech detected before timeout.")
    return got_speech

def speech_to_text():
    """Transcribes audio using the OpenAI transcription API."""
    url = f"{OPENAI_BASE}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    with open(AUDIO_FILE, "rb") as f:
        files = {"file": (AUDIO_FILE, f, "audio/wav")}
        data = {
            "model": STT_MODEL,
            "response_format": "json"
        }
        # Without a timeout a stalled connection hangs the turn forever.
        response = HTTP.post(url, headers=headers, files=files, data=data, timeout=30)

    if response.status_code == 200:
        return response.json().get("text", "").strip()
    else:
        print("STT Error:", response.text)
        return ""

def _trim_history():
    """Bound conversation history without orphaning a tool result.

    The old version deleted a fixed index range, which is unsafe once tool
    calls exist: the API rejects a `tool` message whose matching assistant
    `tool_calls` message has been removed. Trimming forward to the next user
    turn keeps each tool call and its result together.
    """
    while len(conversation_history) > MAX_HISTORY:
        del conversation_history[1]
        while (len(conversation_history) > 1
               and conversation_history[1].get("role") != "user"):
            del conversation_history[1]


def chat_with_llm(user_text):
    """Send the conversation to the chat API, running any tool calls it asks for.

    The model may answer directly, or call one or more tools first (look up a
    file, search the project) and answer using the results. That is a loop,
    not a single request: each round of tool results goes back as context and
    the model may then call another tool. MAX_TOOL_ROUNDS bounds it so a
    model that keeps calling tools can't spin forever with the user waiting.
    """
    url = f"{OPENAI_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    # Refresh on every turn; a date fixed at process startup goes stale when
    # the assistant stays running across midnight.
    local_now = datetime.now().astimezone()
    conversation_history[0]["content"] = (
        SYSTEM_PROMPT + " The current local date and time at the workstation is "
        + local_now.strftime("%A, %B %d, %Y, %I:%M %p %z") + ". "
        "Use this local clock for questions about today or the current time."
    )
    conversation_history.append({"role": "user", "content": user_text})
    _trim_history()

    for _ in range(MAX_TOOL_ROUNDS):
        payload = {
            "model": CHAT_MODEL,
            "messages": conversation_history,
            "tools": registry.chat_schemas(),
            # 1500, not 700: a note or file the model creates travels inside
            # the tool-call arguments, which count against this limit.
            "max_completion_tokens": 1500,
            "reasoning_effort": REASONING_EFFORT,
        }

        response = HTTP.post(url, headers=headers, json=payload, timeout=60)
        LIVENESS.turn_progress()
        if response.status_code != 200:
            print("LLM Error:", response.text[:300])
            return "I encountered an error processing your request."

        message = response.json()["choices"][0]["message"]
        conversation_history.append(message)

        tool_calls = message.get("tool_calls")
        if not tool_calls:
            return (message.get("content") or "").strip()

        for call in tool_calls:
            fn = call["function"]
            print(f"🔧 {fn['name']}({fn.get('arguments', '')[:80]})")
            ui_events.publish("tool", name=fn["name"])
            result = registry.dispatch(fn["name"], fn.get("arguments", "{}"))
            conversation_history.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": result,
            })
        LIVENESS.turn_progress()
        if _cancel.is_set():
            # The tool results stay in the history (the API needs each call
            # answered); the model is simply not asked for another round.
            return ""

    return "I looked into that but couldn't finish working it out."

def _open_tts_stream(text):
    """POST to the speech endpoint and return the streaming response.

    Measured 2026-10-12: some speech requests hang — connected and sent, but
    no response at all (2 of 6 direct calls hit a 30 s limit; 2 of 3 replies
    in one session hit the old 60 s limit, losing the reply). Healthy calls
    answer in 0.6-0.9 s. So wait at most TTS_FIRST_BYTE_TIMEOUT for a reply
    and retry. Retrying here is safe: nothing has played yet. The same read
    timeout then bounds each gap between audio chunks (largest gap logged:
    2.98 s). Returns None if a PTT stop arrives while retrying.
    """
    for attempt in range(1, TTS_ATTEMPTS + 1):
        if _cancel.is_set():
            return None
        try:
            return HTTP.post(
                f"{OPENAI_BASE}/audio/speech",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}",
                         "Content-Type": "application/json"},
                json={"model": TTS_MODEL, "voice": TTS_VOICE, "input": text,
                      "response_format": "pcm"},
                stream=True, timeout=(10, TTS_FIRST_BYTE_TIMEOUT),
            )
        except (requests.ConnectionError, requests.Timeout) as e:
            LIVENESS.turn_progress()      # a retry is progress, not a hang
            if attempt == TTS_ATTEMPTS:
                raise
            print(f"⚠️ TTS attempt {attempt}/{TTS_ATTEMPTS} got no response "
                  f"({type(e).__name__}); retrying")


def speak_response(text, amp_device):
    """Stream the reply's audio to the amp WHILE it is being generated.

    The old version downloaded the whole WAV (2.3 s measured for a two-sentence
    reply), transcoded it with ffmpeg (0.14 s), then played it. Streaming
    starts sound at the first audio chunk instead (~0.8 s measured), and the
    saving grows with reply length.

    Raw PCM goes straight into aplay through ALSA's plughw converter, not
    through Python resampling: resampling each network chunk independently
    puts a small discontinuity at every chunk boundary (an audible buzz at the
    chunk rate), whereas plughw converts one continuous stream. Format
    verified against the API's own WAV header: 24 kHz, mono, 16-bit.

    The volume knob's level is applied per chunk on either path (see
    common/speech_volume.py), and a PTT "stop" (_cancel) ends the reply at
    the next chunk; _interrupt() has already silenced what was queued.

    Returns seconds from request to first audio, or None if nothing played.
    """
    global _current_player
    print(f"\n\U0001F50A Assistant: {text}")
    pcm_device = PLAYBACK_PCM or (amp_device or "").replace("hw:", "plughw:", 1)
    player = None
    first_audio = None
    t0 = time.perf_counter()
    try:
        if _keepalive is not None:
            _keepalive.begin()
        # For amp output, enable before the request so its settle time overlaps
        # the network wait. HDMI playback leaves the MAX amp disabled.
        with (nullcontext() if PLAYBACK_PCM else amp_enable.amplifier()):
            response = _open_tts_stream(text)
            if response is None:        # cancelled while retrying
                return None
            with response as r:
                if r.status_code != 200:
                    print("TTS Error:", r.text[:300])
                    return None
                if _keepalive is None:
                    player = subprocess.Popen(
                        ["aplay", "-D", pcm_device, "-t", "raw", "-f", "S16_LE",
                         "-r", "24000", "-c", "1", "-q", "-"],
                        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    _current_player = player
                    stage = keepalive_output.GainStage(0.0, _volume)

                    def write(chunk):
                        player.stdin.write(stage.process(chunk))
                else:
                    write = _keepalive.write
                for chunk in r.iter_content(4096):
                    if _cancel.is_set():
                        break
                    if not chunk:
                        continue
                    if first_audio is None:
                        first_audio = time.perf_counter() - t0
                        _set_state("speaking")
                    write(chunk)
                    LIVENESS.turn_progress()
            # Let the last buffered audio play before the turn ends.
            if _keepalive:
                _keepalive.drain()
            elif _cancel.is_set():
                player.kill()
            else:
                player.stdin.close()
                player.wait(timeout=120)
    except Exception as e:
        if not _cancel.is_set():
            print("TTS Output Error:", e)
        if player is not None and player.poll() is None:
            player.kill()
    finally:
        _current_player = None
    return first_audio


def run_turn(source, amp_device):
    """One conversation turn: listen, transcribe, think, speak."""
    print(f"\n🎯 Triggered by {source}")
    LIVENESS.turn_started()
    _stop_listening.clear()
    _cancel.clear()
    _set_state("listening")
    idle_detail = None
    try:
        try:
            got_speech = record_audio()
        except (OSError, RuntimeError) as e:
            # Mic missing or unopenable. Counted: a mic that keeps failing is
            # handled by restarting the whole process (see _mic_failed).
            print(f"⚠️ Microphone error: {type(e).__name__}: {e}")
            _mic_failed(e)
            idle_detail = "Microphone problem — try again"
            return
        _mic_ok()
        if _cancel.is_set():
            idle_detail = "Stopped"
            return
        if not got_speech:
            print("💤 No voice detected. Try again.")
            idle_detail = "No speech detected — try again"
            return

        _set_state("thinking", "Transcribing…")
        t_stt = time.perf_counter()
        user_transcript = speech_to_text()
        stt_s = time.perf_counter() - t_stt
        LIVENESS.turn_progress()

        if not user_transcript:
            print("💤 No transcript recognized.")
            idle_detail = "Didn’t catch that — try again"
            return

        print(f"\n🗣️ You: {user_transcript}")
        ui_events.publish("transcript", text=user_transcript)
        _set_state("thinking")

        # Get conversational response from LLM
        t_llm = time.perf_counter()
        ai_response = chat_with_llm(user_transcript)
        llm_s = time.perf_counter() - t_llm
        if _cancel.is_set():
            print("⏹️ Stopped before speaking.")
            idle_detail = "Stopped"
            return

        ui_events.publish("reply", text=ai_response)
        if _volume is not None and _volume.silent():
            # Muted (or turned fully down): show the answer, don't synthesize
            # it — that saves the TTS call and its latency as well.
            print(f"\n\U0001F507 Muted — reply shown on screen: {ai_response}")
            idle_detail = "Muted — reply shown on screen"
            return

        # Speak answer ("speaking" is published at first audio)
        tts_s = speak_response(ai_response, amp_device)
        if _cancel.is_set():
            idle_detail = "Stopped"
        elif tts_s is not None:
            print(f"⏱  STT {stt_s:.2f}s · LLM {llm_s:.2f}s · "
                  f"TTS→sound {tts_s:.2f}s · total after silence "
                  f"{stt_s + llm_s + tts_s:.2f}s (+{SILENCE_MS} ms silence wait)")
    except (requests.RequestException, OSError) as e:
        # Recoverable per turn: a network blip (STT/LLM/TTS) or a mic
        # that couldn't be opened in time (wake-word listener still
        # handing it over). Exiting here would take the assistant down
        # over one bad turn, so report it and wait for the next trigger.
        print(f"⚠️ Turn failed: {type(e).__name__}: {e}")
        ui_events.publish("error", message=f"{type(e).__name__}: {e}")
        idle_detail = "Something went wrong — try again"
    except Exception as e:
        ui_events.publish("error", message=f"{type(e).__name__}: {e}")
        raise
    finally:
        LIVENESS.turn_finished()
        busy.clear()
        _set_state("idle", idle_detail)


if __name__ == "__main__":
    print("==================================================")
    print("🤖 Conversational Voice Assistant Active")
    print(f"🔘 Press the button on GPIO {PTT_PIN} to ask a question.")
    print("==================================================")

    # Liveness first: systemd hears "started" immediately and keeps getting
    # watchdog pings while the assistant waits for its devices.
    LIVENESS.start()
    sd_notify.notify("READY=1")

    amp_device = verify_devices()
    _volume = speech_volume.SpeechVolume()
    if PLAYBACK_PCM:
        amp_enable.disable()
        _keepalive = keepalive_output.KeepAliveOutput(PLAYBACK_PCM, SPEECH_GAIN_DB,
                                                      volume=_volume)
        print("🔊 Keeping the output stream open between replies (silence while idle), "
              f"speech gain {SPEECH_GAIN_DB:+.0f} dB.")
    knob = _start_encoder(_volume)
    _volume.publish()
    _set_state("idle")

    threading.Thread(target=_watch_button, daemon=True).start()
    if WAKE_WORD_ENABLED:
        threading.Thread(target=_watch_wake_word, daemon=True).start()
        print(f"👂 Wake word '{WAKE_WORD}' active (openWakeWord, runs on-device).")
    else:
        print("👂 Wake word disabled (WAKE_WORD_ENABLED=0) — button only.")

    try:
        while True:
            if _fatal.is_set():
                print(f"🛑 Exiting: {_fatal_reason}. Under systemd a fresh process "
                      "starts and waits for the microphone.", flush=True)
                sd_notify.notify("STOPPING=1")
                # os._exit, not sys.exit: skip the atexit PortAudio teardown,
                # which could race a thread still inside a mic read (the
                # SIGABRT documented in common/mic_stream.py).
                os._exit(1)
            try:
                source = trigger_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            busy.set()
            run_turn(source, amp_device)

    except KeyboardInterrupt:
        # Ctrl-C, or systemd stopping the service (KillSignal=SIGINT).
        # Setting busy makes the wake-word listener close its mic stream
        # within one chunk, before PortAudio is torn down at exit.
        sd_notify.notify("STOPPING=1")
        busy.set()
        time.sleep(0.3)
        print("\n🛑 Voice Assistant closed safely.")
        sys.stdout.flush()
