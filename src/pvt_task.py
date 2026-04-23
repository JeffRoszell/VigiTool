"""PVT — Psychomotor Vigilance Task (PsychoPy implementation, Phase 1)"""
from __future__ import annotations

import json
import random
import statistics
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from psychopy import core, visual  # type stubs only — not imported at runtime


# ── Constants ──────────────────────────────────────────────────────────────

ISI_S = {"high": 0.5, "low": 1.5}       # blank screen after response
FOREPERIOD_RANGE = (1.0, 10.0)           # s — fixation to circle onset
STIM_TIMEOUT = 30.0                      # s — max wait before auto-lapse
BLOCK_MINUTES = {"full": 24, "test": 2}
NUM_PERIODS = {"full": 4, "test": 2}
VALID_RT_MIN_MS = 100.0                  # < this = anticipatory
LAPSE_THRESHOLD_MS = 500.0              # > this = lapse
FEEDBACK_DURATION = 1.0                  # s — how long RT is shown


# ── Metrics ────────────────────────────────────────────────────────────────

def compute_metrics(trials: list[dict], pre_stim_anticipatory: int = 0) -> dict:
    """Aggregate performance metrics over all trials."""
    valid_rts = [
        t["reaction_time_ms"] for t in trials
        if t.get("response_type") == "valid" and t.get("reaction_time_ms") is not None
    ]
    lapses = sum(1 for t in trials if t.get("lapse"))
    post_stim_anticipatory = sum(1 for t in trials if t.get("response_type") == "anticipatory")
    total_anticipatory = pre_stim_anticipatory + post_stim_anticipatory

    if valid_rts:
        sorted_rts = sorted(valid_rts)
        n = len(sorted_rts)
        n10 = max(1, n // 10)
        reciprocals = [1000.0 / rt for rt in valid_rts]
        perf = {
            "mean_rt_ms": round(statistics.mean(valid_rts), 2),
            "median_rt_ms": round(statistics.median(valid_rts), 2),
            "std_rt_ms": round(statistics.stdev(valid_rts), 2) if n > 1 else 0.0,
            "min_rt_ms": round(sorted_rts[0], 2),
            "max_rt_ms": round(sorted_rts[-1], 2),
            "fastest_10pct_mean_ms": round(statistics.mean(sorted_rts[:n10]), 2),
            "slowest_10pct_mean_ms": round(statistics.mean(sorted_rts[-n10:]), 2),
            "reciprocal_rt": round(statistics.mean(reciprocals), 4),
        }
    else:
        perf = {
            "mean_rt_ms": None, "median_rt_ms": None, "std_rt_ms": None,
            "min_rt_ms": None, "max_rt_ms": None,
            "fastest_10pct_mean_ms": None, "slowest_10pct_mean_ms": None,
            "reciprocal_rt": None,
        }

    return {
        "total_trials": len(trials),
        "valid_responses": len(valid_rts),
        "anticipatory_responses": total_anticipatory,
        **perf,
        "lapses": lapses,
        "lapse_percentage": round(lapses / len(trials) * 100, 2) if trials else 0.0,
    }


def compute_period_metrics(trials: list[dict], n_periods: int) -> list[dict]:
    result = []
    for p in range(1, n_periods + 1):
        pt = [t for t in trials if t.get("period") == p]
        valid_rts = [
            t["reaction_time_ms"] for t in pt
            if t.get("response_type") == "valid" and t.get("reaction_time_ms") is not None
        ]
        lapses = sum(1 for t in pt if t.get("lapse"))
        result.append({
            "period": p,
            "mean_rt_ms": round(statistics.mean(valid_rts), 2) if valid_rts else None,
            "median_rt_ms": round(statistics.median(valid_rts), 2) if valid_rts else None,
            "lapses": lapses,
        })
    return result


# ── Data I/O ───────────────────────────────────────────────────────────────

def save_data(
    participant_id: str,
    age: int,
    difficulty: str,
    test_mode: bool,
    trials: list[dict],
    pre_stim_anticipatory: int,
    timestamp: str,
) -> Path:
    mode = "test" if test_mode else "full"
    suffix = "_test" if test_mode else ""
    out_dir = Path("data") / participant_id
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = out_dir / f"pvt_{difficulty}{suffix}_{timestamp}.json"

    output = {
        "metadata": {
            "participant_id": participant_id,
            "age": age,
            "task": "pvt",
            "difficulty": difficulty,
            "timestamp": timestamp,
            "isi_ms": int(ISI_S[difficulty] * 1000),
            "block_duration_minutes": BLOCK_MINUTES[mode],
            "foreperiod_range_ms": [
                int(FOREPERIOD_RANGE[0] * 1000),
                int(FOREPERIOD_RANGE[1] * 1000),
            ],
            "is_practice": False,
            "test_mode": test_mode,
        },
        "performance": compute_metrics(trials, pre_stim_anticipatory),
        "period_performance": compute_period_metrics(trials, NUM_PERIODS[mode]),
        "trial_data": trials,
    }

    with filename.open("w") as f:
        json.dump(output, f, indent=2)

    return filename


# ── PsychoPy display helpers ───────────────────────────────────────────────

def _instructions(win: visual.Window, difficulty: str, test_mode: bool) -> bool:
    """Returns False if ESC pressed instead of SPACE."""
    from psychopy import event, visual  # noqa: PLC0415

    pace = "500 ms blank" if difficulty == "high" else "1500 ms blank"
    mins = BLOCK_MINUTES["test" if test_mode else "full"]
    mode_tag = " [TEST MODE]" if test_mode else ""

    body = (
        f"PSYCHOMOTOR VIGILANCE TASK{mode_tag}\n\n"
        f"Difficulty: {difficulty.upper()}  ({pace} between trials)\n"
        f"Duration: {mins} minutes\n\n"
        "A fixation cross (+) will appear at screen centre.\n"
        "After a short wait, a RED CIRCLE will appear.\n\n"
        "Press SPACEBAR as fast as possible when the red circle appears.\n\n"
        "Do not press early — wait for the circle.\n\n"
        "Press SPACEBAR to begin."
    )
    msg = visual.TextStim(
        win, text=body, height=0.06, wrapWidth=1.6,
        color="white", alignText="center",
    )
    msg.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    return "escape" not in (keys or [])


def _results_screen(
    win: visual.Window,
    trials: list[dict],
    pre_stim_anticipatory: int,
    filename: Path,
    n_periods: int,
) -> None:
    from psychopy import event, visual  # noqa: PLC0415

    perf = compute_metrics(trials, pre_stim_anticipatory)
    period_perf = compute_period_metrics(trials, n_periods)

    def _fmt(v: Optional[float], unit: str = " ms") -> str:
        return f"{v:.0f}{unit}" if v is not None else "—"

    lines = [
        "TASK COMPLETE\n",
        f"Total trials:     {perf['total_trials']}",
        f"Valid responses:  {perf['valid_responses']}",
        f"Anticipatory:     {perf['anticipatory_responses']}",
        f"Lapses (>500ms):  {perf['lapses']}  ({perf['lapse_percentage']:.1f}%)",
        "",
        f"Mean RT:    {_fmt(perf['mean_rt_ms'])}",
        f"Median RT:  {_fmt(perf['median_rt_ms'])}",
        f"SD RT:      {_fmt(perf['std_rt_ms'])}",
        f"Fastest 10%: {_fmt(perf['fastest_10pct_mean_ms'])}",
        f"Slowest 10%: {_fmt(perf['slowest_10pct_mean_ms'])}",
        "",
        "Mean RT by period:",
    ]
    for p in period_perf:
        lines.append(f"  Period {p['period']}:  {_fmt(p['mean_rt_ms'])}  "
                     f"(lapses: {p['lapses']})")
    lines += ["", f"Saved to: {filename}", "", "Press ESC to exit."]

    msg = visual.TextStim(
        win, text="\n".join(lines), height=0.055,
        wrapWidth=1.6, color="white", alignText="left",
    )
    msg.draw()
    win.flip()
    event.waitKeys(keyList=["escape"])


# ── Core task loop ─────────────────────────────────────────────────────────

def run_task(
    win: visual.Window,
    difficulty: str,
    block_clock: core.Clock,
    n_periods: int,
    block_s: float,
) -> tuple[list[dict], int, bool]:
    """Returns (trials, pre_stim_anticipatory_count, escaped)."""
    from psychopy import core, event, visual  # noqa: PLC0415

    isi_s = ISI_S[difficulty]
    period_s = block_s / n_periods

    fixation = visual.TextStim(win, text="+", height=0.1, color="white", bold=True)
    circle = visual.Circle(win, radius=0.08, fillColor="red", lineColor="red")
    feedback_obj = visual.TextStim(win, text="", height=0.08, pos=(0, -0.3), bold=True)
    too_early_obj = visual.TextStim(
        win, text="TOO EARLY", height=0.08, color="red", bold=True,
    )

    trials: list[dict] = []
    trial_num = 1
    pre_stim_anticipatory = 0
    first_trial = True

    while block_clock.getTime() < block_s:

        # ── ISI — blank screen ─────────────────────────────
        if not first_trial:
            win.flip()  # blank
            isi_end = block_clock.getTime() + isi_s
            too_early_until = 0.0

            while block_clock.getTime() < isi_end:
                if block_clock.getTime() >= block_s:
                    break
                t_now = block_clock.getTime()
                for k in event.getKeys(["space", "escape"]):
                    if k == "escape":
                        return trials, pre_stim_anticipatory, True
                    if k == "space":
                        pre_stim_anticipatory += 1
                        too_early_until = t_now + 0.5
                if t_now < too_early_until:
                    too_early_obj.draw()
                win.flip()

        first_trial = False
        if block_clock.getTime() >= block_s:
            break

        # ── Fixation foreperiod ────────────────────────────
        foreperiod = random.uniform(*FOREPERIOD_RANGE)
        fp_end = block_clock.getTime() + foreperiod
        too_early_until = 0.0

        while block_clock.getTime() < fp_end:
            if block_clock.getTime() >= block_s:
                break
            t_now = block_clock.getTime()
            for k in event.getKeys(["space", "escape"]):
                if k == "escape":
                    return trials, pre_stim_anticipatory, True
                if k == "space":
                    pre_stim_anticipatory += 1
                    too_early_until = t_now + 0.5
            fixation.draw()
            if t_now < too_early_until:
                too_early_obj.draw()
            win.flip()

        if block_clock.getTime() >= block_s:
            break

        # ── Red circle ─────────────────────────────────────
        stim_onset = block_clock.getTime()
        period = min(int(stim_onset / period_s) + 1, n_periods)

        circle.draw()
        win.flip()
        rt_clock = core.Clock()

        responded = False
        rt_ms: Optional[float] = None

        while rt_clock.getTime() < STIM_TIMEOUT:
            if block_clock.getTime() >= block_s:
                break
            for k, kt in event.getKeys(["space", "escape"], timeStamped=rt_clock):
                if k == "escape":
                    return trials, pre_stim_anticipatory, True
                if k == "space" and not responded:
                    rt_ms = kt * 1000
                    responded = True
            if responded:
                break
            circle.draw()
            win.flip()

        # ── Classify response ──────────────────────────────
        if not responded:
            response_type = "timeout"
            lapse = True
            fb_color = "orange"
            fb_text = "TIMEOUT"
        elif rt_ms < VALID_RT_MIN_MS:
            response_type = "anticipatory"
            lapse = False
            fb_color = "red"
            fb_text = f"{int(rt_ms)} ms  (TOO FAST)"
        elif rt_ms > LAPSE_THRESHOLD_MS:
            response_type = "lapse"
            lapse = True
            fb_color = "orange"
            fb_text = f"{int(rt_ms)} ms"
        else:
            response_type = "valid"
            lapse = False
            fb_color = "white"
            fb_text = f"{int(rt_ms)} ms"

        # ── Feedback ───────────────────────────────────────
        feedback_obj.setColor(fb_color)
        feedback_obj.setText(fb_text)
        fb_end = block_clock.getTime() + FEEDBACK_DURATION

        while block_clock.getTime() < fb_end:
            if block_clock.getTime() >= block_s:
                break
            for k in event.getKeys(["escape"]):
                if k == "escape":
                    return trials, pre_stim_anticipatory, True
            feedback_obj.draw()
            win.flip()

        # ── Record ─────────────────────────────────────────
        trials.append({
            "trial_number": trial_num,
            "period": period,
            "time_on_watch_s": round(stim_onset, 3),
            "foreperiod_ms": round(foreperiod * 1000, 1),
            "reaction_time_ms": round(rt_ms, 2) if rt_ms is not None else None,
            "response_type": response_type,
            "lapse": lapse,
        })
        trial_num += 1

    return trials, pre_stim_anticipatory, False


# ── Entry point ────────────────────────────────────────────────────────────

def main() -> None:
    from psychopy import core, gui  # noqa: PLC0415
    from psychopy import visual as _visual  # noqa: PLC0415

    info: dict = {
        "Participant ID": "",
        "Age": "",
        "Difficulty": ["high", "low"],
        "Test mode": False,
    }
    # copyDict=True works around a bug in PsychoPy 2026.1.3 DlgFromDict.show()
    dlg = gui.DlgFromDict(
        info,
        title="PVT",
        order=["Participant ID", "Age", "Difficulty", "Test mode"],
        sortKeys=False,
        copyDict=True,
    )
    if not dlg.OK:
        core.quit()

    result = dlg.dictionary
    participant_id = str(result["Participant ID"]).strip() or "unknown"
    difficulty = str(result["Difficulty"]).lower()
    test_mode = bool(result["Test mode"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        age = int(result["Age"])
    except ValueError:
        age = 0

    mode = "test" if test_mode else "full"
    n_periods = NUM_PERIODS[mode]
    block_s = BLOCK_MINUTES[mode] * 60.0

    win = _visual.Window(
        fullscr=True,
        color="black",
        units="norm",
        allowGUI=False,
    )
    block_clock = core.Clock()
    trials: list[dict] = []
    pre_stim_anticipatory = 0
    escaped = False

    try:
        if not _instructions(win, difficulty, test_mode):
            escaped = True
        else:
            block_clock.reset()
            trials, pre_stim_anticipatory, escaped = run_task(
                win, difficulty, block_clock, n_periods, block_s,
            )
    finally:
        filename = save_data(
            participant_id, age, difficulty, test_mode,
            trials, pre_stim_anticipatory, timestamp,
        )

    if not escaped:
        _results_screen(win, trials, pre_stim_anticipatory, filename, n_periods)

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
