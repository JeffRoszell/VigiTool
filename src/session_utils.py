"""Shared session-level helpers (window creation, breaks, on-screen messages)."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psychopy import visual  # type stubs only


BREAK_MINUTES = 5.0

# ── Display selection ──────────────────────────────────────────────────────
# Added Sept 2026. The task window was previously created with fullscr=True
# and no screen argument, so it always claimed display 0 and captured the
# cursor there. On the lab machine that meant the RA could not reach iMotions
# on the second monitor, and the task had to be run with that monitor
# physically disconnected — leaving the recording unmonitored for a whole
# session.

DEFAULT_SCREEN = 0
DEFAULT_WINDOW_SIZE = (1280, 720)
FALLBACK_SCREEN_COUNT = 2


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


def make_window(
    *,
    screen: int = DEFAULT_SCREEN,
    fullscr: bool = True,
    size: tuple[int, int] = DEFAULT_WINDOW_SIZE,
    factory=None,
):
    """Single construction point for the task window.

    All three entry points route through here so their window settings cannot
    drift apart. `factory` is injectable so the argument mapping is testable
    without a display.

    Note `units="norm"` stays: norm units are anisotropic on a widescreen, but
    every existing stimulus is laid out in them. The PVT target fixes its own
    roundness by specifying "height" units on the stimulus instead.
    """
    if factory is None:
        from psychopy import visual  # noqa: PLC0415

        factory = visual.Window

    kwargs = {
        "color": "black",
        "units": "norm",
        "screen": int(screen),
        "fullscr": bool(fullscr),
        # A windowed run needs the cursor and window chrome; a fullscreen one
        # must not show them over the stimulus.
        "allowGUI": not fullscr,
    }
    if not fullscr:
        kwargs["size"] = size
    return factory(**kwargs)


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
