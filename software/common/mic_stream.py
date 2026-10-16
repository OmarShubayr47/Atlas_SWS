"""Mic capture resampled to 16kHz for webrtcvad / openWakeWord.

PyAudio opens the raw hardware device by index, which bypasses ALSA's
`plughw` automatic rate conversion (that only happens when a device is
opened through a named ALSA PCM like "plughw:1,0"). Verified against the
actual Corsair mic on this Pi: it only exposes 44100Hz natively — asking
PortAudio to open it directly at 16000Hz raises "Invalid sample rate".
This wraps native-rate capture and resamples to 16kHz in software instead.
"""
import atexit
import threading
import time

import numpy as np
import pyaudio
from scipy.signal import resample_poly

from . import alsa_quiet, audio_devices

TARGET_RATE = 16000
_NATIVE_CHUNK_MS = 30
# The wake-word listener and the PTT/VAD recorder take turns owning the mic
# (see wake_word.py's stop_event) rather than ever holding it concurrently,
# but the handoff isn't instantaneous — the previous owner can still be
# mid-chunk-read or mid-close when the next one tries to open. Retry instead
# of failing on that transient "Device unavailable" instead of only on a
# genuinely absent/dead mic.
_OPEN_RETRIES = 5
_OPEN_RETRY_DELAY_S = 0.15
# Measured on the actual Corsair mic: stream.read() returns literal all-zero
# frames for a variable startup period (a fixed 300ms discard wasn't always
# enough), then jumps straight to the ambient noise floor. That step reads
# as a false speech onset to webrtcvad. Discard adaptively until real
# samples appear, plus a couple more frames to clear the onset transient
# itself, capped so a genuinely dead mic doesn't hang here forever.
_WARMUP_MAX_MS = 2000
_WARMUP_SETTLE_FRAMES = 2

# ---------------------------------------------------------------------------
# One PortAudio instance per process, not per stream.
#
# pyaudio.PyAudio() calls Pa_Initialize() and .terminate() calls
# Pa_Terminate(). Those are process-global and reference-counted inside
# PortAudio — they are NOT per-object, despite the object-shaped API. Creating
# one instance per MicStream therefore means a stream closing in one thread
# tears down PortAudio underneath a stream opening in another.
#
# Observed on hardware: the wake-word listener closed its stream (terminate)
# at the same moment voice_realtime.py opened a new one (initialize), and the
# process died with SIGABRT inside the first read — before a single chunk was
# captured. Because the abort happened while a USB isochronous endpoint was
# live, the controller was left mid-transfer and the kernel then logged
# `xhci-hcd: WARN: buffer overrun event` followed by
# `usb usb1-port2: disabled by hub (EMI?)` and a disconnect. The USB drop was
# a consequence of the crash, not an electrical fault — the mic passed 60s
# continuous-capture and capture-under-network-load endurance tests.
#
# Sharing one instance removes the init/terminate race entirely. It is never
# terminated mid-run; teardown happens once at interpreter exit.
_pa_lock = threading.Lock()
_pa_instance = None


def _get_pyaudio():
    global _pa_instance
    with _pa_lock:
        if _pa_instance is None:
            # Silenced: this is the call that enumerates every ALSA PCM.
            with alsa_quiet.suppressed_c_stderr():
                _pa_instance = pyaudio.PyAudio()
        return _pa_instance


@atexit.register
def _shutdown_pyaudio():
    global _pa_instance
    with _pa_lock:
        if _pa_instance is not None:
            try:
                with alsa_quiet.suppressed_c_stderr():
                    _pa_instance.terminate()
            except Exception:
                pass
            _pa_instance = None
# ---------------------------------------------------------------------------


class MicStream:
    def __init__(self, name_hint: str = "CORSAIR", target_rate: int = TARGET_RATE):
        """target_rate is a parameter, not the module constant, because the
        consumers disagree: webrtcvad and openWakeWord want 16kHz, while the
        OpenAI Realtime API wants 24kHz. The mic's native rate (44100 here)
        is resampled to whichever is asked for."""
        self._target_rate = target_rate
        self._pa = _get_pyaudio()
        self._device_index = audio_devices.find_pyaudio_input_index(name_hint, self._pa)
        info = self._pa.get_device_info_by_index(self._device_index)
        self.native_rate = int(info["defaultSampleRate"])
        self._native_chunk = int(self.native_rate * _NATIVE_CHUNK_MS / 1000)
        self._stream = self._open_with_retry()
        self._buffer = np.array([], dtype=np.int16)
        self._warm_up()

    def _open_with_retry(self):
        # PortAudio prints four lines of C-level internals to stderr on every
        # failed open. For an attempt we're about to retry that's pure noise —
        # and on a contended device it printed 20 lines per turn. The Python
        # OSError carries the same diagnosis ("[Errno -9985] Device
        # unavailable") more legibly, so keep the exception and drop the
        # spam. The final attempt is left loud: if we're about to give up,
        # every scrap of detail is worth having.
        for attempt in range(1, _OPEN_RETRIES + 1):
            last_attempt = attempt == _OPEN_RETRIES
            try:
                if last_attempt:
                    return self._open_stream()
                with alsa_quiet.suppressed_c_stderr():
                    return self._open_stream()
            except OSError:
                if last_attempt:
                    raise
                time.sleep(_OPEN_RETRY_DELAY_S)

    def _open_stream(self):
        return self._pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.native_rate,
            input=True,
            input_device_index=self._device_index,
            frames_per_buffer=self._native_chunk,
        )

    def _warm_up(self) -> None:
        max_chunks = max(1, int(_WARMUP_MAX_MS / _NATIVE_CHUNK_MS))
        for _ in range(max_chunks):
            raw = self._stream.read(self._native_chunk, exception_on_overflow=False)
            if np.frombuffer(raw, dtype=np.int16).any():
                break
        # A couple more frames to get past the silence->signal onset transient.
        for _ in range(_WARMUP_SETTLE_FRAMES):
            self._stream.read(self._native_chunk, exception_on_overflow=False)

    def read_ms(self, ms: int) -> bytes:
        """Returns `ms` milliseconds of mono 16-bit PCM at self._target_rate."""
        needed = int(self._target_rate * ms / 1000)
        while len(self._buffer) < needed:
            raw = self._stream.read(self._native_chunk, exception_on_overflow=False)
            native = np.frombuffer(raw, dtype=np.int16)
            if self.native_rate == self._target_rate:
                resampled = native
            else:
                resampled = np.clip(
                    resample_poly(native, self._target_rate, self.native_rate), -32768, 32767
                ).astype(np.int16)
            self._buffer = np.concatenate([self._buffer, resampled])
        out, self._buffer = self._buffer[:needed], self._buffer[needed:]
        return out.tobytes()

    def close(self):
        """Close this stream only.

        Deliberately does NOT call self._pa.terminate() — the PyAudio
        instance is shared process-wide (see above). Terminating here would
        tear PortAudio down underneath any other stream still running, which
        is what caused the SIGABRT.
        """
        try:
            self._stream.stop_stream()
        finally:
            self._stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
