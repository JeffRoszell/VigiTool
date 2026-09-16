"""Shared session-level helpers (window creation, breaks, on-screen messages)."""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, NamedTuple, Optional

if TYPE_CHECKING:
    from psychopy import visual  # type stubs only


BREAK_MINUTES = 5.0

# ── Display selection ──────────────────────────────────────────────────────
# Added Sept 2026. The task window was previously created with fullscr=True
# and no screen argument, so it always opened on display 0. On the lab
# machine the RA could not reach iMotions on the second monitor, and the task
# had to be run with that monitor physically disconnected — leaving the
# recording unmonitored for a whole session.
#
# Display modes (Sept 2026, second lab run): with the display fixed, iMotions
# screen recording — and the Windows Snipping Tool — still could not capture
# the task in fullscreen. A borderless, fullscreen-sized OpenGL window is
# typically handed straight to the display by Windows/the GPU driver,
# bypassing the desktop compositor that screen capture reads from. The
# "borderless" mode is an ordinary undecorated window sized to the screen,
# which stays composited and therefore capturable. It is trimmed by
# BORDERLESS_TRIM_PX so it does not exactly cover the monitor, because an
# exact cover is what drivers use to promote a window to that fast path.
# Compositing may add up to one frame of display latency to every trial, so
# the mode is recorded in the output and must not be mixed across
# participants.

DEFAULT_SCREEN = 0
DEFAULT_WINDOW_SIZE = (1280, 720)
FALLBACK_SCREEN_COUNT = 2

DISPLAY_MODES = ("fullscreen", "borderless", "windowed")
DISPLAY_MODE_LABELS = ("Fullscreen", "Borderless", "Windowed")
DEFAULT_DISPLAY_MODE = "fullscreen"
BORDERLESS_TRIM_PX = 1


class ScreenGeometry(NamedTuple):
    """A screen as the OS reports it, plus the panel's real resolution.

    ``x, y, width, height`` are the desktop coordinates pyglet reports, which
    on Windows are *scaled* for a DPI-unaware process: a 1920x1080 panel at
    125% scaling reports as 1536x864. ``panel_width/height`` come from the
    current display mode, which is not scaled, so the two disagree exactly
    when Windows display scaling is above 100%. None when unknown.
    """

    x: int
    y: int
    width: int
    height: int
    panel_width: Optional[int] = None
    panel_height: Optional[int] = None


class WindowGeometry(NamedTuple):
    x: int
    y: int
    width: int
    height: int


def screen_count() -> int:
    """Number of displays PsychoPy can see, or a permissive fallback.

    Detection goes through pyglet's canvas. If that is unavailable the
    fallback assumes a second display may exist, so an RA who genuinely has
    two monitors is not blocked by a failed probe.
    """
    try:
        import pyglet  # noqa: PLC0415

        return max(1, len(pyglet.canvas.get_display().get_screens()))
    except Exception:  # noqa: BLE001 — a probe failure must never stop a session
        return FALLBACK_SCREEN_COUNT


def to_screen_index(display_number: int) -> int:
    """Convert a 1-based dialog choice to PsychoPy's 0-based screen index.

    The dialog is 1-based because RAs think in terms of "Display 2". Doing
    the conversion once, here, keeps the off-by-one out of the call sites.
    """
    return max(0, int(display_number) - 1)


def resolve_screen_index(
    display_number: int, count: int | None = None,
) -> tuple[int, bool]:
    """Return (screen_index, fell_back).

    Display indices come from the OS and reorder when a monitor is unplugged
    or over remote desktop, so a stored choice can point at a display that is
    no longer there. Depending on backend and version PsychoPy either falls
    back silently or crashes; neither is acceptable mid-session, so an
    out-of-range choice is clamped to the primary display and the caller is
    told, so it can warn.
    """
    index = to_screen_index(display_number)
    available = screen_count() if count is None else count
    if index >= available:
        return DEFAULT_SCREEN, True
    return index, False


def normalize_display_mode(choice: str) -> str:
    """Map a dialog label ("Borderless") to its mode key ("borderless").

    Raises ValueError on anything else, so a typo cannot silently fall
    through to a different mode than the one the RA picked.
    """
    mode = str(choice).strip().lower()
    if mode not in DISPLAY_MODES:
        raise ValueError(f"Unknown display mode {choice!r}; expected one of {DISPLAY_MODES}")
    return mode


def screen_geometry(index: int) -> ScreenGeometry | None:
    """Probe the geometry of screen `index`, or None if it cannot be read."""
    try:
        import pyglet  # noqa: PLC0415

        screen = pyglet.canvas.get_display().get_screens()[index]
    except Exception:  # noqa: BLE001 — a probe failure must never stop a session
        return None
    panel_w = panel_h = None
    try:
        mode = screen.get_mode()
        panel_w, panel_h = int(mode.width), int(mode.height)
    except Exception:  # noqa: BLE001, S110 — the panel size is advisory only
        pass
    return ScreenGeometry(
        int(screen.x), int(screen.y), int(screen.width), int(screen.height),
        panel_w, panel_h,
    )


def borderless_size(geometry: ScreenGeometry, trim_px: int = BORDERLESS_TRIM_PX) -> tuple[int, int]:
    """Window size for borderless mode: the full width, trimmed height."""
    return geometry.width, max(1, geometry.height - int(trim_px))


def make_window(
    *,
    screen: int = DEFAULT_SCREEN,
    mode: str = DEFAULT_DISPLAY_MODE,
    size: tuple[int, int] = DEFAULT_WINDOW_SIZE,
    geometry: ScreenGeometry | None = None,
    trim_px: int = BORDERLESS_TRIM_PX,
    factory=None,
):
    """Single construction point for the task window.

    All three entry points route through here so their window settings cannot
    drift apart. `factory` is injectable so the argument mapping is testable
    without a display.

    Borderless mode needs the screen's geometry; if it is not supplied and
    cannot be probed this raises ValueError rather than guessing a size — use
    `open_task_window`, which falls back to fullscreen and records that.

    Note `units="norm"` stays: norm units are anisotropic on a widescreen, but
    every existing stimulus is laid out in them. The PVT target fixes its own
    roundness by specifying "height" units on the stimulus instead.
    """
    mode = normalize_display_mode(mode)
    if factory is None:
        from psychopy import visual  # noqa: PLC0415

        factory = visual.Window

    kwargs = {
        "color": "black",
        "units": "norm",
        "screen": int(screen),
        "fullscr": mode == "fullscreen",
        # Only a windowed run shows the cursor and window chrome; the
        # participant must never see them over the stimulus.
        "allowGUI": mode == "windowed",
    }
    if mode == "windowed":
        kwargs["size"] = size
    elif mode == "borderless":
        if geometry is None:
            geometry = screen_geometry(int(screen))
        if geometry is None:
            raise ValueError("Borderless mode needs the screen geometry, which could not be read")
        kwargs["size"] = borderless_size(geometry, trim_px)
        # PsychoPy offsets `pos` by the chosen screen's origin, so (0, 0) is
        # that screen's top-left corner, not the primary display's.
        kwargs["pos"] = (0, 0)
    return factory(**kwargs)


def window_geometry(win) -> WindowGeometry | None:
    """Where the window actually landed, from the pyglet handle, or None."""
    try:
        handle = win.winHandle
        x, y = handle.get_location()
        w, h = handle.get_size()
        return WindowGeometry(int(x), int(y), int(w), int(h))
    except Exception:  # noqa: BLE001 — geometry is advisory, never fatal
        return None


def display_problems(
    mode: str,
    geometry: ScreenGeometry | None,
    actual: WindowGeometry | None,
    *,
    trim_px: int = BORDERLESS_TRIM_PX,
    platform: str | None = None,
) -> list[str]:
    """Plain-language reasons the window may not match the screen.

    Empty means no problem was detected. Windowed mode is exempt: it is not
    meant to cover the screen. The scaling check is Windows-only, because on
    macOS a Retina panel legitimately reports more pixels than points.
    """
    mode = normalize_display_mode(mode)
    if mode == "windowed":
        return []
    if geometry is None:
        return ["The screen's size and position could not be read."]

    problems: list[str] = []
    platform = sys.platform if platform is None else platform
    if (
        platform == "win32"
        and geometry.panel_width
        and geometry.panel_height
        and (geometry.panel_width, geometry.panel_height) != (geometry.width, geometry.height)
    ):
        problems.append(
            f"Windows reports this screen as {geometry.width}x{geometry.height}, but the "
            f"panel is {geometry.panel_width}x{geometry.panel_height}. Display scaling "
            "is probably above 100%."
        )

    if actual is not None:
        if mode == "borderless":
            expected_size = borderless_size(geometry, trim_px)
            if (actual.x, actual.y) != (geometry.x, geometry.y):
                problems.append(
                    f"The window is at ({actual.x}, {actual.y}) but the screen starts at "
                    f"({geometry.x}, {geometry.y})."
                )
        else:
            expected_size = (geometry.width, geometry.height)
        if (actual.width, actual.height) != expected_size:
            problems.append(
                f"The window is {actual.width}x{actual.height} but should be "
                f"{expected_size[0]}x{expected_size[1]}."
            )
    return problems


def build_display_meta(
    *,
    screen: int,
    requested_mode: str,
    mode: str,
    geometry: ScreenGeometry | None,
    actual: WindowGeometry | None,
    problems: list[str],
    refresh_hz: float | None = None,
) -> dict:
    """The `metadata.display` block written to every task JSON.

    `fullscreen` is kept (true only for fullscreen mode) so analysis code
    written against the earlier {"screen", "fullscreen"} block still works.
    """
    return {
        "screen": int(screen),
        "fullscreen": mode == "fullscreen",
        "mode": mode,
        "requested_mode": requested_mode,
        "screen_geometry": None if geometry is None else {
            "x": geometry.x, "y": geometry.y,
            "width": geometry.width, "height": geometry.height,
        },
        "panel_resolution": (
            None if geometry is None or geometry.panel_width is None
            else [geometry.panel_width, geometry.panel_height]
        ),
        "window_geometry": None if actual is None else actual._asdict(),
        "borderless_trim_px": BORDERLESS_TRIM_PX if mode == "borderless" else 0,
        "refresh_hz": None if refresh_hz is None else round(float(refresh_hz), 2),
        "size_mismatch": bool(problems),
        "problems": list(problems),
    }


def measure_refresh_hz(win) -> float | None:
    """Measured refresh rate, or None if PsychoPy cannot settle on one."""
    try:
        rate = win.getActualFrameRate(nIdentical=20, nMaxFrames=120, threshold=1)
    except Exception:  # noqa: BLE001 — advisory only
        return None
    return None if rate is None else float(rate)


def open_task_window(
    display_number: int,
    mode: str = DEFAULT_DISPLAY_MODE,
    *,
    factory=None,
    probe=screen_geometry,
    count: int | None = None,
    measure: bool = True,
):
    """Resolve the display, open the window and check it against the screen.

    Returns ``(win, display_meta, fell_back, problems)``. The caller shows
    `display_warning_body` when `fell_back` and `display_mismatch_body` when
    `problems` is non-empty, before the participant is seated.

    If borderless is requested but the screen cannot be probed, the window
    opens fullscreen instead and `display_meta` records both modes, so a run
    that silently changed mode is still identifiable in the data.
    """
    requested = normalize_display_mode(mode)
    screen, fell_back = resolve_screen_index(display_number, count)
    geometry = probe(screen)
    effective = requested
    if requested == "borderless" and geometry is None:
        effective = "fullscreen"
    win = make_window(screen=screen, mode=effective, geometry=geometry, factory=factory)
    actual = window_geometry(win)
    problems = display_problems(effective, geometry, actual)
    if effective != requested:
        problems.insert(0, "Borderless mode was selected but could not be used; "
                           "the task opened fullscreen instead.")
    refresh = measure_refresh_hz(win) if measure else None
    meta = build_display_meta(
        screen=screen, requested_mode=requested, mode=effective,
        geometry=geometry, actual=actual, problems=problems, refresh_hz=refresh,
    )
    return win, meta, fell_back, problems


def display_mismatch_body(problems: list[str]) -> str:
    listed = "\n".join(f"- {p}" for p in problems)
    return (
        "DISPLAY SIZE MISMATCH\n\n"
        f"{listed}\n\n"
        "Stimuli may be scaled or offset, and gaze may not line up with them.\n"
        "Experimenter: set Windows display scaling to 100% for this screen,\n"
        "or press ESC to abort and relaunch.\n\n"
        "Press SPACEBAR to continue anyway (this is recorded in the data)."
    )


def display_warning_body(requested: int) -> str:
    return (
        "DISPLAY NOT FOUND\n\n"
        f"Display {requested} was selected, but the system reports fewer\n"
        "displays than that. The task is running on Display 1 instead.\n\n"
        "Experimenter: check the monitor connection before seating the\n"
        "participant, or press ESC to abort and relaunch.\n\n"
        "Press SPACEBAR to continue on Display 1."
    )


def timed_break(
    win: visual.Window,
    minutes: float = BREAK_MINUTES,
    label: str = "BREAK",
) -> bool:
    """Show a countdown screen for the given duration. ESC aborts.

    Returns True if the break completed normally, False if ESC was pressed.
    """
    from psychopy import core, event, visual  # noqa: PLC0415

    end_t = core.getTime() + minutes * 60.0
    text_obj = visual.TextStim(
        win, text="", height=0.08, color="white",
        alignText="center", wrapWidth=1.6,
    )

    last_drawn_secs = -1
    while True:
        remaining = end_t - core.getTime()
        if remaining <= 0:
            return True
        for k in event.getKeys(["escape"]):
            if k == "escape":
                return False

        secs_total = int(remaining + 0.5)
        if secs_total != last_drawn_secs:
            mins = secs_total // 60
            secs = secs_total % 60
            text_obj.setText(
                f"{label}\n\n{mins:02d}:{secs:02d}\n\n"
                "Please rest. The next block will start automatically."
            )
            last_drawn_secs = secs_total
        text_obj.draw()
        win.flip()
        core.wait(0.05)


def recalibration_hold(
    win: visual.Window,
    marker_client=None,
    eye_tracker: str | None = None,
) -> bool:
    """RA hold screen for eye-tracking recalibration after a break.

    Per the PI decision (June 2026, Jeff_questions_U2 Q10): the 5-minute
    breaks require eye-tracking recalibration because the participant may
    have shifted. Originally "between 24-minute blocks and between tasks";
    since Sept 2026 the PVT is a single 10-minute block, so the breaks are
    between the two CVT blocks and between tasks — two holds per session. The screen holds
    until the RA confirms recalibration in iMotions; the interval is
    bracketed with recalibration_start/end markers so it can be excluded
    from analysis epochs.

    ``eye_tracker`` is the display name of the Smart Eye device (e.g. "Aurora",
    "AI-X"); when provided it is shown on the hold screen so the RA knows which
    device to recalibrate.

    Returns True to continue, False on ESC.
    """
    if marker_client is not None:
        marker_client.discrete("recalibration_start")
    device = f" ({eye_tracker})" if eye_tracker else ""
    body = (
        f"EYE-TRACKING RECALIBRATION{device}\n\n"
        "Experimenter: the participant may have shifted during the break.\n"
        "Recalibrate the eye tracker in iMotions now, then press SPACEBAR\n"
        "to begin the next block."
    )
    ok = message_screen(win, body)
    if marker_client is not None:
        marker_client.discrete("recalibration_end")
    return ok


def message_screen(
    win: visual.Window,
    body: str,
    accept_keys: tuple[str, ...] = ("space",),
    abort_keys: tuple[str, ...] = ("escape",),
) -> bool:
    """Show a message and wait for a key. Returns True on accept, False on abort."""
    from psychopy import event, visual  # noqa: PLC0415

    msg = visual.TextStim(
        win, text=body, height=0.06, wrapWidth=1.6,
        color="white", alignText="center",
    )
    msg.draw()
    win.flip()
    keys = event.waitKeys(keyList=list(accept_keys) + list(abort_keys))
    return not any(k in abort_keys for k in (keys or []))
