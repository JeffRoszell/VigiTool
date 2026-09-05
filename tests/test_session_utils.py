"""Tests for session_utils — no PsychoPy required.

Display selection: make_window takes an injectable factory, so the argument
mapping is assertable without opening a window. What cannot be tested here is
that the window physically lands on the right panel — that is a manual check
in docs/visual_smoke_test.md.

recalibration_hold:

The hold screen itself needs a window, so message_screen is monkeypatched;
these tests pin the marker contract: a recalibration_start/end pair brackets
the RA hold, and the RA's ESC abort is propagated.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import session_utils
from session_utils import (
    DEFAULT_SCREEN,
    make_window,
    recalibration_hold,
    resolve_screen_index,
    screen_count,
    to_screen_index,
)


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


# -- Display selection ------------------------------------------------------

class _FakeWindow:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_make_window_defaults_to_fullscreen_on_the_primary_display():
    win = make_window(factory=_FakeWindow)
    assert win.kwargs["screen"] == DEFAULT_SCREEN
    assert win.kwargs["fullscr"] is True
    assert win.kwargs["allowGUI"] is False
    assert win.kwargs["units"] == "norm"
    assert "size" not in win.kwargs  # fullscreen takes the whole panel


def test_make_window_uses_the_selected_screen():
    # Regression: the window previously always claimed display 0, trapping the
    # cursor there and leaving iMotions unreachable on the second monitor.
    win = make_window(screen=1, factory=_FakeWindow)
    assert win.kwargs["screen"] == 1
    assert win.kwargs["fullscr"] is True


def test_windowed_mode_shows_chrome_and_sets_a_size():
    win = make_window(fullscr=False, factory=_FakeWindow)
    assert win.kwargs["fullscr"] is False
    assert win.kwargs["allowGUI"] is True  # the RA needs the cursor back
    assert win.kwargs["size"] == session_utils.DEFAULT_WINDOW_SIZE


def test_display_choice_is_one_based():
    # The dialog says "Display 2"; PsychoPy counts from zero.
    assert to_screen_index(1) == 0
    assert to_screen_index(2) == 1
    assert to_screen_index(0) == 0  # never negative


def test_resolve_screen_index_clamps_to_an_existing_display():
    # An index the OS no longer has must fall back, not crash mid-session.
    assert resolve_screen_index(2, count=2) == (1, False)
    assert resolve_screen_index(3, count=2) == (DEFAULT_SCREEN, True)
    assert resolve_screen_index(2, count=1) == (DEFAULT_SCREEN, True)


def test_screen_count_is_at_least_one():
    assert screen_count() >= 1
