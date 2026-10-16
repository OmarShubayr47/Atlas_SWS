"""Model compatibility and listener handoff checks; no microphone or cloud calls.

Run with the project venv: .venv/bin/python tests/test_wake_word.py
"""
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "software"))
from common import wake_word


class WakeWordTests(unittest.TestCase):
    def test_atlas_loads_and_predicts_from_another_directory(self):
        previous = Path.cwd()
        try:
            with tempfile.TemporaryDirectory() as directory:
                os.chdir(directory)
                model = wake_word.Model(
                    wakeword_model_paths=[wake_word._model_path("hey_atlas")]
                )
                self.assertEqual(list(model.models), ["hey_atlas"])
                for _ in range(30):
                    score = model.predict(np.zeros(1280, dtype=np.int16))["hey_atlas"]
                    self.assertTrue(np.isfinite(score))
                    self.assertLess(score, wake_word.DEFAULT_THRESHOLD)
        finally:
            os.chdir(previous)

    def test_existing_model_override(self):
        path = Path(wake_word._model_path("hey_jarvis"))
        self.assertTrue(path.is_file())
        self.assertIn("hey_jarvis", path.name)

    def test_unknown_model_reports_available_models(self):
        with self.assertRaisesRegex(RuntimeError, "No openWakeWord model.*not_a_model.*hey_atlas"):
            wake_word._model_path("not_a_model")

    def test_missing_atlas_reports_file_without_falling_back(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(wake_word, "ATLAS_MODEL_PATH", Path(directory) / "absent.onnx"):
                with self.assertRaisesRegex(RuntimeError, "hey_atlas model is missing"):
                    wake_word._model_path("hey_atlas")

    def test_detection_uses_loaded_key_and_closes_microphone(self):
        model = MagicMock()
        model.models = {"loaded_model_key": object()}
        model.predict.side_effect = [{"loaded_model_key": 0.1}, {"loaded_model_key": 0.9}]
        with patch.object(wake_word, "Model", return_value=model):
            with patch.object(wake_word.mic_stream, "MicStream") as stream:
                stream.return_value.__enter__.return_value.read_ms.return_value = bytes(2560)
                self.assertTrue(wake_word.listen_for_wake_word())
                self.assertEqual(model.predict.call_count, 2)
                stream.return_value.__exit__.assert_called_once()

    def test_ptt_stop_releases_microphone_during_listening(self):
        stop = threading.Event()
        model = MagicMock()
        model.models = {"hey_atlas": object()}
        model.predict.return_value = {"hey_atlas": 0.0}

        def read_frame(_ms):
            stop.set()  # Simulate the PTT trigger while the listener owns the mic.
            return bytes(2560)

        with patch.object(wake_word, "Model", return_value=model):
            with patch.object(wake_word.mic_stream, "MicStream") as stream:
                stream.return_value.__enter__.return_value.read_ms.side_effect = read_frame
                self.assertFalse(wake_word.listen_for_wake_word(stop_event=stop))
                self.assertEqual(model.predict.call_count, 1)
                stream.return_value.__exit__.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
