"""_open_tts_stream: retry speech requests that hang (2026-10-12).

voice_assistant.py claims GPIO at import, so the helper is loaded on its own
from the source and run against stand-ins for the HTTP session and PTT stop.
"""
import ast
import pathlib
import threading
from unittest.mock import MagicMock

import pytest
import requests

SOURCE = pathlib.Path(__file__).resolve().parents[2] / "software" / "voice_assistant.py"


def load_helper(post):
    tree = ast.parse(SOURCE.read_text())
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "_open_tts_stream")
    env = {
        "requests": requests, "HTTP": MagicMock(post=post), "LIVENESS": MagicMock(),
        "_cancel": threading.Event(), "OPENAI_BASE": "https://example.invalid/v1",
        "OPENAI_API_KEY": "test", "TTS_MODEL": "m", "TTS_VOICE": "v",
        "TTS_FIRST_BYTE_TIMEOUT": 8.0, "TTS_ATTEMPTS": 3,
    }
    exec(compile(ast.Module([fn], []), str(SOURCE), "exec"), env)
    return env["_open_tts_stream"], env


def test_recovers_after_two_hangs():
    ok = object()
    post = MagicMock(side_effect=[requests.ReadTimeout(), requests.ReadTimeout(), ok])
    helper, env = load_helper(post)
    assert helper("hello") is ok
    assert post.call_count == 3
    assert post.call_args.kwargs["timeout"] == (10, 8.0)
    assert post.call_args.kwargs["stream"] is True
    assert env["LIVENESS"].turn_progress.call_count == 2


def test_gives_up_after_three_attempts():
    post = MagicMock(side_effect=requests.ConnectionError())
    helper, _ = load_helper(post)
    with pytest.raises(requests.ConnectionError):
        helper("hello")
    assert post.call_count == 3


def test_ptt_stop_ends_retrying():
    helper, env = load_helper(None)

    def hang_then_stop(*a, **k):
        env["_cancel"].set()          # owner pressed stop during the wait
        raise requests.ReadTimeout()

    env["HTTP"].post = MagicMock(side_effect=hang_then_stop)
    assert helper("hello") is None
    assert env["HTTP"].post.call_count == 1


def test_other_errors_are_not_retried():
    post = MagicMock(side_effect=ValueError("bad"))
    helper, _ = load_helper(post)
    with pytest.raises(ValueError):
        helper("hello")
    assert post.call_count == 1
