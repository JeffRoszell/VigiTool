"""Top-level session orchestrator: runs CVT and PVT back-to-back.

The application leaves task and difficulty order to RAs. Counterbalancing is
managed externally; this script just collects the choices, runs the chosen
sequence, and enforces the timed 5-minute break between tasks.

EEG baseline is recorded once at the very start of the session (per IRB). A
hold screen prompts the experimenter to confirm the baseline is captured
before the first task begins.

The PVT has no difficulty factor (Sept 2026), so the two tasks no longer take
the same arguments; per-task keyword options are built by build_task_options.

iMotions integration (Phase 2): when enabled, opens one continuous Event
Receiving API connection at the start of the session and emits markers
across CVT, PVT, and the break (per PI decision: one continuous recording).
Optional Remote Control API auto-starts/stops the iMotions recording —
default off until the wire format is verified on the lab machine.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import cvt_task
import imotions_config
import pvt_task
from imotions_api import EventReceivingAPI, LoggingMarkerClient, RemoteControlAPI
from session_utils import (
    BREAK_MINUTES,
    message_screen,
    recalibration_hold,
    timed_break,
)

logger = logging.getLogger(__name__)

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


def parse_difficulty_order(label: str) -> tuple[str, str]:
    """Map a dialog label onto a difficulty pair."""
    return ("high", "low") if str(label).startswith("high") else ("low", "high")


def build_task_options(dialog: dict) -> dict[str, dict]:
    """Map raw dialog fields onto per-task keyword arguments.

    The tasks no longer take a uniform argument list: the CVT has a
    high/low difficulty factor and a practice block, the PVT has neither.
    Keeping that divergence in a table here — rather than branching on the
    task name inside the dispatch loop — means the loop contains no protocol
    knowledge, and adding or removing a per-task factor is a one-line edit.
    """
    return {
        "cvt": {
            "difficulty_order": parse_difficulty_order(dialog["CVT difficulty order"]),
            "skip_practice": False,
        },
        "pvt": {},
    }


def run(
    participant_id: str,
    task_order: tuple[str, str],
    task_options: dict[str, dict],
    test_mode: bool,
    *,
    break_minutes: float = BREAK_MINUTES,
) -> bool:
    """Run a full session. Returns True if escaped early."""
    from psychopy import core  # noqa: PLC0415
    from psychopy import visual as _visual  # noqa: PLC0415

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cfg = imotions_config.load()

    # ── iMotions setup ─────────────────────────────────────────────
    # One continuous Event Receiving API connection spans the whole
    # session (per PI decision May 2026). Remote Control API is opened
    # only if the feature flag is on. The marker stream is teed to a
    # per-session sidecar log for post-hoc debugging of iMotions issues.
    raw_event_client = EventReceivingAPI(
        host=cfg.host, port=cfg.event_port, enabled=cfg.event_enabled,
    )
    raw_event_client.connect()
    log_path = Path("data") / participant_id / f"session_{timestamp}.imotions.log"
    event_client = LoggingMarkerClient(raw_event_client, log_path)

    remote_client: RemoteControlAPI | None = None
    if cfg.remote_enabled:
        remote_client = RemoteControlAPI(
            host=cfg.host, port=cfg.remote_port, enabled=True,
        )
        remote_client.connect()

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

        # Begin the iMotions recording (if remote enabled) once the EEG
        # baseline confirmation is in. Then bracket the whole session with
        # a session_<pid>_<ts> scene so offline analysis can find it easily.
        if remote_client is not None:
            remote_client.start_study(cfg.study_name, participant_id)
        session_label = f"session_{participant_id}_{timestamp}"
        event_client.scene_start(
            session_label,
            description=f"pid={participant_id},eye_tracker={cfg.eye_tracker}",
        )

        tracker_display = cfg.eye_tracker_display
        for i, task in enumerate(task_order):
            # Everything after participant_id goes by keyword. The PVT's
            # difficulty_order slot was removed in Sept 2026, and passing
            # positionally would silently slide test_mode into its place.
            escaped = runners[task](
                win,
                participant_id,
                test_mode=test_mode,
                timestamp=timestamp,
                break_minutes=break_minutes,
                marker_client=event_client,
                eye_tracker=tracker_display,
                **task_options.get(task, {}),
            )
            if escaped:
                return True

            if i < len(task_order) - 1:
                event_client.discrete("session_break_start")
                ok = timed_break(win, minutes=break_minutes, label="BREAK BETWEEN TASKS")
                event_client.discrete("session_break_end")
                if not ok:
                    return True
                # Per PI decision (June 2026): breaks require eye-tracking
                # recalibration before the next task begins.
                if not recalibration_hold(
                    win, event_client, eye_tracker=tracker_display,
                ):
                    return True
    finally:
        try:
            event_client.scene_end(f"session_{participant_id}_{timestamp}")
        except Exception as exc:  # noqa: BLE001 — never let teardown raise
            logger.warning("iMotions session scene_end failed: %s", exc)
        if remote_client is not None:
            try:
                remote_client.stop_study()
            except Exception as exc:  # noqa: BLE001
                logger.warning("iMotions stop_study failed: %s", exc)
            remote_client.close()
        event_client.close()
        win.close()
        core.quit()

    return False


def main() -> None:
    from psychopy import core, gui  # noqa: PLC0415

    info: dict = {
        "Participant ID": "",
        "Task order": ["CVT → PVT", "PVT → CVT"],
        "CVT difficulty order": ["high → low", "low → high"],
        "Test mode": False,
    }
    dlg = gui.DlgFromDict(
        info,
        title="Vigilance Session",
        order=[
            "Participant ID",
            "Task order",
            "CVT difficulty order",
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

    run(participant_id, task_order, build_task_options(result), test_mode)


if __name__ == "__main__":
    main()
