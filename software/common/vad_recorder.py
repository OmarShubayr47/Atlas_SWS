"""Stream mic audio and stop recording once the user finishes speaking.

Replaces a fixed-duration `arecord -d N` call, which either truncates long
utterances or wastes time listening to silence after short ones. Classifies
each 30ms frame as speech/silence with webrtcvad over a resampled mic stream
(see mic_stream.py for why raw PyAudio capture needs resampling here).
"""
import wave

import webrtcvad

from . import mic_stream

SAMPLE_RATE = mic_stream.TARGET_RATE  # webrtcvad only accepts 8000/16000/32000/48000 Hz
FRAME_MS = 30  # webrtcvad frames must be exactly 10, 20, or 30 ms
# Measured on hardware: a freshly constructed webrtcvad.Vad misclassifies the
# first several frames as speech regardless of their actual content — its
# internal state needs a few frames to settle. Priming with throwaway calls
# before trusting is_speech() avoids a spurious "speech" onset at recording
# start.
_VAD_PRIME_FRAMES = 10


def record_until_silence(
    out_path: str,
    mic_name_hint: str = "CORSAIR",
    vad_aggressiveness: int = 2,
    silence_ms: int = 800,
    max_seconds: float = 15.0,
    listen_timeout_s: float = 6.0,
    stop_event=None,
    on_progress=None,
) -> bool:
    """Record to out_path until `silence_ms` of continuous silence follows
    detected speech, or `max_seconds` is reached (safety cap so a stuck or
    noisy mic can't record forever).

    If no speech starts within `listen_timeout_s` of opening the stream,
    aborts and returns False without writing a file, so a false wake-word
    trigger or an empty button press doesn't feed silence into STT/LLM.

    `stop_event` ends the recording early, e.g. a second PTT press meaning
    "I'm done talking": what was said so far is kept. Set before any speech
    started, it means "never mind" and returns False. `on_progress` is
    called per frame for the liveness supervisor (common/liveness.py).
    """
    vad = webrtcvad.Vad(vad_aggressiveness)

    frames = []
    speech_started = False
    silence_frame_count = 0
    silence_frames_needed = silence_ms // FRAME_MS
    listen_timeout_frames = int(listen_timeout_s * 1000 / FRAME_MS)
    max_frames = int(max_seconds * 1000 / FRAME_MS)
    frames_read = 0

    with mic_stream.MicStream(mic_name_hint) as mic:
        for _ in range(_VAD_PRIME_FRAMES):
            vad.is_speech(mic.read_ms(FRAME_MS), SAMPLE_RATE)

        while frames_read < max_frames:
            if stop_event is not None and stop_event.is_set():
                if not speech_started:
                    return False
                break
            chunk = mic.read_ms(FRAME_MS)
            frames_read += 1
            if on_progress is not None:
                on_progress()
            is_speech = vad.is_speech(chunk, SAMPLE_RATE)

            if not speech_started:
                if is_speech:
                    speech_started = True
                    frames.append(chunk)
                elif frames_read >= listen_timeout_frames:
                    return False
                continue

            frames.append(chunk)
            if is_speech:
                silence_frame_count = 0
            else:
                silence_frame_count += 1
                if silence_frame_count >= silence_frames_needed:
                    break

    if not frames:
        return False

    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return True
