"""Streaming playback of Realtime API audio through the I2S amp.

The Realtime API returns mono 16-bit PCM at 24kHz in incremental chunks as
the model speaks. The amp is driven at 48kHz stereo S32_LE (the format the
existing pipeline already proved works on this card). Three conversions are
needed, and one of them is free:

  rate     24000 -> 48000   exactly 2x, so resample_poly(x, 2, 1) is an
                            integer upsample with no awkward fractional ratio
  channels mono  -> stereo  duplicate the single channel to both
  width    int16 -> int32   left-shift 16 bits (preserves full scale)

Playback streams into a long-lived `aplay` process via stdin rather than
writing a file and playing it afterwards. Writing files would reintroduce the
whole-response latency that using a streaming API is meant to remove: the
first syllable can play while the model is still generating the last one.

`stop()` exists for barge-in. Audio already handed to aplay is committed —
ALSA is buffering it — so interrupting means killing the process outright
rather than politely draining it.
"""
import subprocess

import numpy as np
from scipy.signal import resample_poly

SOURCE_RATE = 24000  # Realtime API native output rate
PLAYBACK_RATE = 48000
PLAYBACK_CHANNELS = 2


def _to_amp_format(pcm16_mono_24k: bytes) -> bytes:
    """24kHz mono int16 -> 48kHz stereo int32, ready for aplay."""
    mono = np.frombuffer(pcm16_mono_24k, dtype=np.int16)
    if mono.size == 0:
        return b""

    upsampled = resample_poly(mono, PLAYBACK_RATE // SOURCE_RATE, 1)
    upsampled = np.clip(upsampled, -32768, 32767).astype(np.int32)

    # int16 -> int32 full scale. Done after clipping so the shift can't
    # overflow the int32 range.
    widened = upsampled << 16

    stereo = np.repeat(widened[:, np.newaxis], PLAYBACK_CHANNELS, axis=1)
    return stereo.astype("<i4").tobytes()


class StreamingPlayer:
    """Feeds converted audio to `aplay` as it arrives.

    The aplay process is started lazily on the first write, so an assistant
    turn that produces no audio never spawns one, and idle time doesn't hold
    the playback device open (which would block anything else using the amp).
    """

    def __init__(self, amp_device: str):
        self._amp_device = amp_device
        self._proc: subprocess.Popen | None = None

    def _ensure_proc(self) -> subprocess.Popen:
        if self._proc is None or self._proc.poll() is not None:
            self._proc = subprocess.Popen(
                [
                    "aplay",
                    "-D", self._amp_device,
                    "-f", "S32_LE",
                    "-r", str(PLAYBACK_RATE),
                    "-c", str(PLAYBACK_CHANNELS),
                    "-q",             # suppress the "Playing raw data" banner
                    "-",              # read from stdin
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return self._proc

    def write(self, pcm16_mono_24k: bytes) -> None:
        data = _to_amp_format(pcm16_mono_24k)
        if not data:
            return
        proc = self._ensure_proc()
        try:
            proc.stdin.write(data)
            proc.stdin.flush()
        except (BrokenPipeError, ValueError):
            # aplay died (device yanked, or stop() raced us). Drop the chunk
            # rather than killing the whole conversation over it; the next
            # write will respawn the process.
            self._proc = None

    def stop(self) -> None:
        """Cut playback immediately, discarding anything still buffered."""
        if self._proc is None:
            return
        proc, self._proc = self._proc, None
        try:
            proc.kill()
            proc.wait(timeout=1)
        except Exception:
            pass

    def finish(self) -> None:
        """Let queued audio drain, then close. Use at the end of a turn."""
        if self._proc is None:
            return
        proc, self._proc = self._proc, None
        try:
            proc.stdin.close()
            proc.wait(timeout=30)
        except Exception:
            proc.kill()
