"""Always-listening wake-word detector using openWakeWord.

The default "hey_atlas" model is bundled in software/models; see that
directory's README for its source, license restrictions and test status.
The installed openWakeWord models remain available through WAKE_WORD.

Runs fully on-device (ONNX via onnxruntime, CPU execution provider on the
Pi 5 — no GPU, none expected) so continuous listening doesn't stream audio
to a cloud API just to detect a wake word.
"""
import warnings
from pathlib import Path

import numpy as np

# onnxruntime warns that CUDAExecutionProvider isn't available on every model
# load. That's expected and permanent here — the Pi 5 has no GPU and none is
# planned (see module docstring); it falls back to CPU, which is the intended
# execution provider. Filtered narrowly by message so genuine onnxruntime
# warnings still surface.
warnings.filterwarnings(
    "ignore",
    message=r".*CUDAExecutionProvider.*",
    category=UserWarning,
)

from openwakeword import get_pretrained_model_paths  # noqa: E402
from openwakeword.model import Model  # noqa: E402

from . import mic_stream

CHUNK_MS = 80  # openWakeWord's typical frame size
DEFAULT_WAKE_WORD = "hey_atlas"
ATLAS_MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "hey_atlas.onnx"

# Starting point only — has not been tuned against this room's noise floor
# or mic placement. Lower it if wake-ups are missed, raise it if it false-
# triggers on background speech/TV audio.
DEFAULT_THRESHOLD = 0.5


def _model_path(wake_word: str) -> str:
    if wake_word == "hey_atlas":
        if not ATLAS_MODEL_PATH.is_file():
            raise RuntimeError(f"Bundled hey_atlas model is missing: {ATLAS_MODEL_PATH}")
        return str(ATLAS_MODEL_PATH)
    for path in get_pretrained_model_paths():
        if wake_word in path:
            return path
    available = ", ".join(get_pretrained_model_paths())
    raise RuntimeError(
        f"No openWakeWord model matches '{wake_word}'. "
        f"Available: hey_atlas (bundled), {available}"
    )


def listen_for_wake_word(
    wake_word: str = DEFAULT_WAKE_WORD,
    mic_name_hint: str = "CORSAIR",
    threshold: float = DEFAULT_THRESHOLD,
    stop_event=None,
    on_progress=None,
) -> bool:
    """Blocks until the wake word is detected (returns True) or `stop_event`
    is set (returns False).

    `stop_event` matters because this holds the mic open for as long as it
    runs: the USB mic on this Pi doesn't support concurrent capture opens,
    so if the PTT button fires while this is mid-listen, the button's VAD
    recorder can't open its own stream until this one lets go. Checking the
    event every chunk (~CHUNK_MS) instead of only between calls closes that
    window instead of leaving it to whenever the wake word next fires.

    `on_progress` is called once per chunk read, so a supervisor can tell a
    listener that is quietly waiting for "Hey Atlas" from one stuck inside
    the audio driver (see common/liveness.py). It must be cheap.
    """
    model = Model(wakeword_model_paths=[_model_path(wake_word)])
    model_key = next(iter(model.models.keys()))

    with mic_stream.MicStream(mic_name_hint) as mic:
        while True:
            if stop_event is not None and stop_event.is_set():
                return False
            chunk = mic.read_ms(CHUNK_MS)
            if on_progress is not None:
                on_progress()
            audio = np.frombuffer(chunk, dtype=np.int16)
            scores = model.predict(audio)
            if scores[model_key] >= threshold:
                return True
