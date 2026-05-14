"""Top-level session orchestrator: runs CVT and PVT back-to-back.

The application leaves task and difficulty order to RAs. Counterbalancing is
managed externally; this script just collects the choices, runs the chosen
sequence, and enforces the timed 5-minute break between tasks.

EEG baseline is recorded once at the very start of the session (per IRB). A
hold screen prompts the experimenter to confirm the baseline is captured
before the first task begins.

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
from session_utils import BREAK_MINUTES, message_screen, timed_break

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
        event_client.scene_start(session_label, description=f"pid={participant_id}")

        for i, task in enumerate(task_order):
            kwargs = {"break_minutes": break_minutes, "marker_client": event_client}
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
                event_client.discrete("session_break_start")
                ok = timed_break(win, minutes=break_minutes, label="BREAK BETWEEN TASKS")
                event_client.discrete("session_break_end")
                if not ok:
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
