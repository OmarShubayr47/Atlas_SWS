"""Shared setup for the pure-logic unit tests (no GPIO, mic or projector).

Run:  .venv/bin/python -m pytest tests/unit -q
"""
import os
import pathlib
import sys

# Before any project import: never POST test events to a running UI server.
os.environ["UI_EVENTS"] = "0"

SOFTWARE = pathlib.Path(__file__).resolve().parents[2] / "software"
sys.path.insert(0, str(SOFTWARE))
