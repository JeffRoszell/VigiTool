"""Shared session-level helpers (timed break, on-screen messages)."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psychopy import visual  # type stubs only


BREAK_MINUTES = 5.0


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
    breaks between 24-minute blocks and between tasks require eye-tracking
    recalibration because the participant may have shifted. The screen holds
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
