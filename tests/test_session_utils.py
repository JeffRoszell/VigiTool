"""Tests for session_utils.recalibration_hold — no PsychoPy required.

The hold screen itself needs a window, so message_screen is monkeypatched;
these tests pin the marker contract: a recalibration_start/end pair brackets
the RA hold, and the RA's ESC abort is propagated.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import session_utils
from session_utils import recalibration_hold


class _FakeMarkerClient:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def discrete(self, name, description=""):
        self.calls.append(("discrete", name, description))

    def scene_start(self, name, description="", media="I"):
        self.calls.append(("scene_start", name, description, media))

    def scene_end(self, name):
        self.calls.append(("scene_end", name))


def test_recalibration_markers_bracket_hold(monkeypatch):
    fake = _FakeMarkerClient()
    monkeypatch.setattr(session_utils, "message_screen", lambda win, body: True)
    assert recalibration_hold(None, fake) is True
    assert fake.calls == [
        ("discrete", "recalibration_start", ""),
        ("discrete", "recalibration_end", ""),
    ]


def test_recalibration_esc_propagates_and_still_closes_marker(monkeypatch):
    fake = _FakeMarkerClient()
    monkeypatch.setattr(session_utils, "message_screen", lambda win, body: False)
    assert recalibration_hold(None, fake) is False
    # end marker still emitted so the interval is closed in the stream
    assert fake.calls == [
        ("discrete", "recalibration_start", ""),
        ("discrete", "recalibration_end", ""),
    ]


def test_recalibration_without_marker_client(monkeypatch):
    monkeypatch.setattr(session_utils, "message_screen", lambda win, body: True)
    assert recalibration_hold(None, None) is True


def test_recalibration_screen_mentions_recalibration(monkeypatch):
    seen = {}

    def _capture(win, body):
        seen["body"] = body
        return True

    monkeypatch.setattr(session_utils, "message_screen", _capture)
    recalibration_hold(None, None)
    assert "RECALIBRATION" in seen["body"].upper()
    assert "SPACEBAR" in seen["body"]
