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
import pytest
from session_utils import (
    BORDERLESS_TRIM_PX,
    DEFAULT_SCREEN,
    DISPLAY_MODE_LABELS,
    DISPLAY_MODES,
    ScreenGeometry,
    WindowGeometry,
    build_display_meta,
    display_mismatch_body,
    display_problems,
    make_window,
    normalize_display_mode,
    open_task_window,
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


# A second monitor to the right of a 1920x1080 primary.
SECOND = ScreenGeometry(1920, 0, 1920, 1080, 1920, 1080)


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
    win = make_window(mode="windowed", factory=_FakeWindow)
    assert win.kwargs["fullscr"] is False
    assert win.kwargs["allowGUI"] is True  # the RA needs the cursor back
    assert win.kwargs["size"] == session_utils.DEFAULT_WINDOW_SIZE


def test_borderless_is_an_undecorated_non_fullscreen_window():
    # Regression: iMotions screen recording could not capture fullscreen.
    win = make_window(screen=1, mode="borderless", geometry=SECOND, factory=_FakeWindow)
    assert win.kwargs["fullscr"] is False  # stays composited, so capturable
    assert win.kwargs["allowGUI"] is False  # no chrome, no cursor for the participant
    assert win.kwargs["screen"] == 1
    assert win.kwargs["pos"] == (0, 0)  # PsychoPy offsets by the screen origin


def test_borderless_is_trimmed_so_it_does_not_exactly_cover_the_screen():
    win = make_window(mode="borderless", geometry=SECOND, factory=_FakeWindow)
    assert BORDERLESS_TRIM_PX == 1
    assert win.kwargs["size"] == (1920, 1080 - BORDERLESS_TRIM_PX)
    untrimmed = make_window(mode="borderless", geometry=SECOND, trim_px=0, factory=_FakeWindow)
    assert untrimmed.kwargs["size"] == (1920, 1080)


def test_borderless_without_geometry_refuses_to_guess(monkeypatch):
    monkeypatch.setattr(session_utils, "screen_geometry", lambda index: None)
    with pytest.raises(ValueError):
        make_window(mode="borderless", factory=_FakeWindow)


def test_dialog_labels_map_to_modes_and_fullscreen_is_the_default():
    assert [normalize_display_mode(label) for label in DISPLAY_MODE_LABELS] == list(DISPLAY_MODES)
    # DlgFromDict uses the first list element as the default.
    assert normalize_display_mode(DISPLAY_MODE_LABELS[0]) == "fullscreen"
    with pytest.raises(ValueError):
        normalize_display_mode("Full screen")


# -- Geometry checks --------------------------------------------------------

def test_no_problems_when_the_window_matches_the_screen():
    fitted = WindowGeometry(1920, 0, 1920, 1079)
    assert display_problems("borderless", SECOND, fitted, platform="win32") == []
    full = WindowGeometry(1920, 0, 1920, 1080)
    assert display_problems("fullscreen", SECOND, full, platform="win32") == []


def test_windows_display_scaling_is_detected():
    # A 1920x1080 panel at 125% scaling reports as 1536x864.
    scaled = ScreenGeometry(0, 0, 1536, 864, 1920, 1080)
    problems = display_problems("fullscreen", scaled, None, platform="win32")
    assert len(problems) == 1
    assert "scaling" in problems[0]


def test_scaling_check_is_windows_only():
    # A Retina panel legitimately reports more pixels than points.
    retina = ScreenGeometry(0, 0, 1512, 982, 3024, 1964)
    assert display_problems("fullscreen", retina, None, platform="darwin") == []


def test_misplaced_or_missized_borderless_window_is_detected():
    offset = WindowGeometry(0, 0, 1920, 1079)  # landed on the primary display
    assert any("screen starts at" in p for p in
               display_problems("borderless", SECOND, offset, platform="win32"))
    small = WindowGeometry(1920, 0, 1536, 864)
    assert any("should be 1920x1079" in p for p in
               display_problems("borderless", SECOND, small, platform="win32"))


def test_windowed_mode_is_exempt_and_missing_geometry_is_reported():
    assert display_problems("windowed", None, None) == []
    assert display_problems("borderless", None, None) != []


def test_display_meta_records_mode_geometry_and_problems():
    meta = build_display_meta(
        screen=1, requested_mode="borderless", mode="borderless", geometry=SECOND,
        actual=WindowGeometry(1920, 0, 1920, 1079), problems=[], refresh_hz=60.013,
    )
    assert meta["screen"] == 1
    assert meta["mode"] == "borderless"
    assert meta["fullscreen"] is False  # kept for older analysis code
    assert meta["screen_geometry"] == {"x": 1920, "y": 0, "width": 1920, "height": 1080}
    assert meta["panel_resolution"] == [1920, 1080]
    assert meta["window_geometry"] == {"x": 1920, "y": 0, "width": 1920, "height": 1079}
    assert meta["borderless_trim_px"] == BORDERLESS_TRIM_PX
    assert meta["refresh_hz"] == 60.01
    assert meta["size_mismatch"] is False


def test_open_task_window_falls_back_to_fullscreen_and_says_so():
    win, meta, fell_back, problems = open_task_window(
        1, "Borderless", factory=_FakeWindow, probe=lambda i: None, count=1, measure=False,
    )
    assert win.kwargs["fullscr"] is True
    assert meta["requested_mode"] == "borderless"
    assert meta["mode"] == "fullscreen"
    assert meta["size_mismatch"] is True
    assert fell_back is False
    assert "could not be used" in problems[0]


def test_open_task_window_borderless_on_the_second_display():
    win, meta, fell_back, problems = open_task_window(
        2, "Borderless", factory=_FakeWindow, probe=lambda i: SECOND, count=2, measure=False,
    )
    assert win.kwargs["screen"] == 1
    assert win.kwargs["size"] == (1920, 1079)
    assert meta["mode"] == meta["requested_mode"] == "borderless"
    assert fell_back is False
    assert problems == []  # a fake window has no handle, so only the probe is checked


def test_mismatch_warning_lists_problems_and_keys():
    body = display_mismatch_body(["The window is 1536x864 but should be 1920x1079."])
    assert "DISPLAY SIZE MISMATCH" in body
    assert "1536x864" in body
    assert "SPACEBAR" in body and "ESC" in body


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
