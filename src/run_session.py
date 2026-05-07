"""Top-level session orchestrator: runs CVT and PVT back-to-back.

The application leaves task and difficulty order to RAs. Counterbalancing is
managed externally; this script just collects the choices, runs the chosen
sequence, and enforces the timed 5-minute break between tasks.

EEG baseline is recorded once at the very start of the session (per IRB). A
hold screen prompts the experimenter to confirm the baseline is captured
before the first task begins.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import cvt_task
import pvt_task
from session_utils import BREAK_MINUTES, message_screen, timed_break

if TYPE_CHECKING:
    from psychopy import visual  # type stubs only


def _eeg_baseline_hold(win: visual.Window) -> bool:
    """Pre-task hold screen for EEG baseline. Returns False on ESC."""
    body = (
        "EEG BASELINE\n\n"
        "The session will begin with a brief EEG baseline recording.\n\n"
        "Experimenter: confirm electrodes are connected and baseline is\n"
        "running, then press SPACEBAR to continue to the first task."
    )
    return message_screen(win, body)


def run(
    participant_id: str,
    task_order: tuple[str, str],
    difficulty_orders: dict[str, tuple[str, str]],
    test_mode: bool,
    *,
    break_minutes: float = BREAK_MINUTES,
) -> bool:
    """Run a full session. Returns True if escaped early."""
    from psychopy import core  # noqa: PLC0415
    from psychopy import visual as _visual  # noqa: PLC0415

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    win = _visual.Window(
        fullscr=True,
        color="black",
        units="norm",
        allowGUI=False,
    )

    runners = {"cvt": cvt_task.run_full_session, "pvt": pvt_task.run_full_session}

    try:
        if not _eeg_baseline_hold(win):
            return True

        for i, task in enumerate(task_order):
            kwargs = {"break_minutes": break_minutes}
            if task == "cvt":
                kwargs["skip_practice"] = False
            escaped = runners[task](
                win,
                participant_id,
                difficulty_orders[task],
                test_mode,
                timestamp,
                **kwargs,
            )
            if escaped:
                return True

            if i < len(task_order) - 1:
                if not timed_break(win, minutes=break_minutes, label="BREAK BETWEEN TASKS"):
                    return True
    finally:
        win.close()
        core.quit()

    return False


def main() -> None:
    from psychopy import core, gui  # noqa: PLC0415

    info: dict = {
        "Participant ID": "",
        "Task order": ["CVT → PVT", "PVT → CVT"],
        "CVT difficulty order": ["high → low", "low → high"],
        "PVT difficulty order": ["high → low", "low → high"],
        "Test mode": False,
    }
    dlg = gui.DlgFromDict(
        info,
        title="Vigilance Session",
        order=[
            "Participant ID",
            "Task order",
            "CVT difficulty order",
            "PVT difficulty order",
            "Test mode",
        ],
        sortKeys=False,
        copyDict=True,
    )
    if not dlg.OK:
        core.quit()

    result = dlg.dictionary
    participant_id = str(result["Participant ID"]).strip() or "unknown"
    task_order_str = str(result["Task order"])
    test_mode = bool(result["Test mode"])

    task_order = ("cvt", "pvt") if task_order_str.startswith("CVT") else ("pvt", "cvt")

    def _diff(label: str) -> tuple[str, str]:
        s = str(result[label])
        return ("high", "low") if s.startswith("high") else ("low", "high")

    difficulty_orders = {
        "cvt": _diff("CVT difficulty order"),
        "pvt": _diff("PVT difficulty order"),
    }

    run(participant_id, task_order, difficulty_orders, test_mode)


if __name__ == "__main__":
    main()
