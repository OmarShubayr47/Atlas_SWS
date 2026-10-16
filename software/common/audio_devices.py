"""Resolve ALSA capture/playback devices by name instead of hard-coded card indices.

CLAUDE.md: "ALSA card indices are NOT stable across reboots. Resolve by name,
never hard-code." This module implements that lookup for both directions
(arecord -l for capture, aplay -l for playback) by parsing the same
'card N: ID [DESC], device D: ...' lines the ALSA tools print.
"""
import re
import subprocess

_CARD_LINE = re.compile(r"^card (\d+): (\S+) \[([^\]]+)\]")


def _list_cards(kind: str) -> list[tuple[int, str, str]]:
    """kind: 'capture' or 'playback'. Returns [(index, id, description), ...]."""
    cmd = "arecord" if kind == "capture" else "aplay"
    result = subprocess.run([cmd, "-l"], capture_output=True, text=True, check=True)
    cards = []
    for line in result.stdout.splitlines():
        m = _CARD_LINE.match(line)
        if m:
            cards.append((int(m.group(1)), m.group(2), m.group(3)))
    return cards


def find_card_index(name_hint: str, kind: str) -> int:
    """Find the ALSA card index whose id or description contains name_hint
    (case-insensitive). Raises if none or more than one match, since a
    silent guess defeats the point of resolving by name."""
    hint = name_hint.lower()
    cards = _list_cards(kind)
    matches = [c for c in cards if hint in c[1].lower() or hint in c[2].lower()]

    if not matches:
        available = ", ".join(f"{i}:{cid}" for i, cid, _ in cards) or "(none found)"
        raise RuntimeError(
            f"No {kind} card matching '{name_hint}'. Available cards: {available}. "
            f"Check the device is connected and `{'arecord' if kind == 'capture' else 'aplay'} -l` "
            f"shows it."
        )
    if len(matches) > 1:
        found = ", ".join(f"{i}:{cid}" for i, cid, _ in matches)
        raise RuntimeError(
            f"'{name_hint}' matches more than one {kind} card ({found}). "
            f"Use a more specific name_hint."
        )
    return matches[0][0]


def mic_device(name_hint: str = "CORSAIR", subdevice: int = 0) -> str:
    """plughw string for the USB mic. plughw (not hw) lets ALSA resample if the
    mic's native rate/format doesn't match what we request (16kHz S16_LE mono)."""
    idx = find_card_index(name_hint, "capture")
    return f"plughw:{idx},{subdevice}"


def amp_device(name_hint: str = "hifiberry", subdevice: int = 0) -> str:
    """hw string for the I2S amp (hifiberry-dac overlay). Returned as hw:, not
    plughw:, so each caller decides on conversion: voice_assistant.py swaps it
    to plughw: to let ALSA convert 24 kHz mono TTS, while audio_out.py already
    converts to S32_LE stereo itself."""
    idx = find_card_index(name_hint, "playback")
    return f"hw:{idx},{subdevice}"


def find_pyaudio_input_index(name_hint: str, pyaudio_instance) -> int:
    """PortAudio (used by PyAudio, needed for streaming capture — VAD and
    wake-word both read frames directly rather than shelling out to arecord)
    enumerates devices with its own index, separate from the ALSA card index
    used by arecord/aplay. Match by the same name substring instead."""
    hint = name_hint.lower()
    matches = []
    for i in range(pyaudio_instance.get_device_count()):
        info = pyaudio_instance.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0 and hint in info["name"].lower():
            matches.append(i)

    if not matches:
        raise RuntimeError(f"No PyAudio input device matching '{name_hint}' found.")
    if len(matches) > 1:
        raise RuntimeError(
            f"'{name_hint}' matches more than one PyAudio input device: {matches}. "
            f"Use a more specific name_hint."
        )
    return matches[0]
