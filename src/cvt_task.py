"""CVT — Cognitive Vigilance Task (PsychoPy implementation, Phase 1)"""
from __future__ import annotations

import json
import math
import random
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from psychopy import core, visual  # type stubs only — not imported at runtime


# ── Constants ──────────────────────────────────────────────────────────────

STIM_DURATION = 1.0           # s
ISI_S = {"high": 0.5, "low": 1.5}
BLOCK_MINUTES = {"full": 24, "test": 2}
NUM_PERIODS = {"full": 4, "test": 2}
SIGNALS_PER_PERIOD = {"full": 5, "test": 3}
FEEDBACK_DURATION = 0.3        # s

# Quadrant centres in norm units, origin at screen centre
QUADRANT_POS = {
    "upper_left":  (-0.5,  0.5),
    "upper_right": ( 0.5,  0.5),
    "lower_left":  (-0.5, -0.5),
    "lower_right": ( 0.5, -0.5),
}
JITTER = 0.05   # ± norm units


# ── Trial generation ───────────────────────────────────────────────────────

def _critical_signal() -> str:
    d1 = random.randint(0, 9)
    d2 = random.choice([d for d in (d1 - 1, d1, d1 + 1) if 0 <= d <= 9])
    return f"{d1}{d2}"


def _non_signal() -> str:
    while True:
        d1, d2 = random.randint(0, 9), random.randint(0, 9)
        if abs(d1 - d2) > 1:
            return f"{d1}{d2}"


def build_trial_sequence(difficulty: str, test_mode: bool) -> list[dict]:
    """Pure function — no external deps, directly unit-testable."""
    mode = "test" if test_mode else "full"
    trial_cycle = STIM_DURATION + ISI_S[difficulty]
    period_s = BLOCK_MINUTES[mode] * 60 / NUM_PERIODS[mode]
    trials_per_period = int(period_s / trial_cycle)
    sigs = SIGNALS_PER_PERIOD[mode]

    trials: list[dict] = []
    trial_num = 1
    quadrants = list(QUADRANT_POS.keys())

    for period in range(1, NUM_PERIODS[mode] + 1):
        signal_slots = set(random.sample(range(trials_per_period), sigs))

        for i in range(trials_per_period):
            is_sig = i in signal_slots
            trials.append({
                "trial_number": trial_num,
                "period": period,
                "stimulus": _critical_signal() if is_sig else _non_signal(),
                "is_signal": is_sig,
                "quadrant": random.choice(quadrants),
                "time_on_watch_ms": None,
                "response_made": False,
                "reaction_time_ms": None,
                "outcome": None,
            })
            trial_num += 1

    return trials


# ── SDT metrics ────────────────────────────────────────────────────────────

def _norm_ppf(p: float) -> float:
    """Inverse normal CDF — Abramowitz & Stegun 26.2.17 (max error 4.5e-4)."""
    c = (2.515517, 0.802853, 0.010328)
    d = (1.432788, 0.189269, 0.001308)

    q = p if p <= 0.5 else 1.0 - p
    t = math.sqrt(-2.0 * math.log(q))
    z = t - (c[0] + t * (c[1] + t * c[2])) / (1.0 + t * (d[0] + t * (d[1] + t * d[2])))
    return -z if p <= 0.5 else z


def _z(hits: int, total: int) -> float:
    """Hautus (1995) log-linear correction avoids 0/1 boundary problems."""
    return _norm_ppf((hits + 0.5) / (total + 1))


def compute_sdt(trials: list[dict]) -> dict:
    signals = [t for t in trials if t["is_signal"]]
    nonsignals = [t for t in trials if not t["is_signal"]]

    hits = sum(1 for t in signals if t.get("outcome") == "hit")
    misses = sum(1 for t in signals if t.get("outcome") == "miss")
    fas = sum(1 for t in nonsignals if t.get("outcome") == "false_alarm")
    crs = sum(1 for t in nonsignals if t.get("outcome") == "correct_rejection")

    n_sig = hits + misses
    n_ns = fas + crs

    z_h = _z(hits, n_sig) if n_sig else 0.0
    z_f = _z(fas, n_ns) if n_ns else 0.0

    hit_rts = [
        t["reaction_time_ms"] for t in trials
        if t.get("outcome") == "hit" and t.get("reaction_time_ms") is not None
    ]

    return {
        "hits": hits,
        "misses": misses,
        "false_alarms": fas,
        "correct_rejections": crs,
        "hit_rate": round((hits + 0.5) / (n_sig + 1), 4) if n_sig else 0.0,
        "false_alarm_rate": round((fas + 0.5) / (n_ns + 1), 4) if n_ns else 0.0,
        "d_prime": round(z_h - z_f, 4),
        "criterion": round(-0.5 * (z_h + z_f), 4),
        "mean_rt_hits_ms": round(sum(hit_rts) / len(hit_rts), 2) if hit_rts else None,
    }


def compute_period_metrics(trials: list[dict], n_periods: int) -> list[dict]:
    result = []
    for p in range(1, n_periods + 1):
        pt = [t for t in trials if t.get("period") == p]
        m = compute_sdt(pt)
        result.append({
            "period": p,
            "hit_rate": m["hit_rate"],
            "false_alarm_rate": m["false_alarm_rate"],
            "d_prime": m["d_prime"],
            "mean_rt_hits_ms": m["mean_rt_hits_ms"],
        })
    return result


# ── Data I/O ───────────────────────────────────────────────────────────────

def save_data(
    participant_id: str,
    age: int,
    difficulty: str,
    test_mode: bool,
    trials: list[dict],
    timestamp: str,
) -> Path:
    mode = "test" if test_mode else "full"
    suffix = "_test" if test_mode else ""
    out_dir = Path("data") / participant_id
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = out_dir / f"cvt_{difficulty}{suffix}_{timestamp}.json"

    output = {
        "metadata": {
            "participant_id": participant_id,
            "age": age,
            "task": "cvt",
            "difficulty": difficulty,
            "timestamp": timestamp,
            "stimulus_duration_ms": int(STIM_DURATION * 1000),
            "isi_ms": int(ISI_S[difficulty] * 1000),
            "block_duration_minutes": BLOCK_MINUTES[mode],
            "total_signals": SIGNALS_PER_PERIOD[mode] * NUM_PERIODS[mode],
            "is_practice": False,
            "test_mode": test_mode,
        },
        "performance": compute_sdt(trials),
        "period_performance": compute_period_metrics(trials, NUM_PERIODS[mode]),
        "trial_data": trials,
    }

    with filename.open("w") as f:
        json.dump(output, f, indent=2)

    return filename


# ── PsychoPy display helpers ───────────────────────────────────────────────
# Imports deferred so pure functions above are testable without PsychoPy.

def _jittered_pos(quadrant: str) -> tuple[float, float]:
    x, y = QUADRANT_POS[quadrant]
    return (
        x + random.uniform(-JITTER, JITTER),
        y + random.uniform(-JITTER, JITTER),
    )


def _instructions(win: visual.Window, difficulty: str, test_mode: bool) -> bool:
    """Show instructions. Returns False if ESC pressed instead of SPACE."""
    from psychopy import event, visual  # noqa: PLC0415

    pace = "500 ms blank" if difficulty == "high" else "1500 ms blank"
    mins = BLOCK_MINUTES["test" if test_mode else "full"]
    mode_tag = " [TEST MODE]" if test_mode else ""

    body = (
        f"COGNITIVE VIGILANCE TASK{mode_tag}\n\n"
        f"Difficulty: {difficulty.upper()}  ({pace} between stimuli)\n"
        f"Duration: {mins} minutes\n\n"
        "Two-digit numbers will appear one at a time.\n\n"
        "Press SPACEBAR only when the digit difference is 0 or ±1\n"
        "  Examples  YES:  45  67  88  32\n"
        "            NO:   28  73  19\n\n"
        "You may respond during the number or the blank that follows it.\n\n"
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
    filename: Path,
    n_periods: int,
) -> None:
    from psychopy import event, visual  # noqa: PLC0415

    perf = compute_sdt(trials)
    period_perf = compute_period_metrics(trials, n_periods)

    n_total = perf["hits"] + perf["misses"]
    rt_str = f"{perf['mean_rt_hits_ms']:.0f} ms" if perf["mean_rt_hits_ms"] else "—"

    lines = [
        "TASK COMPLETE\n",
        f"Hits:            {perf['hits']} / {n_total}",
        f"False alarms:    {perf['false_alarms']}",
        f"d′:               {perf['d_prime']:.2f}",
        f"Criterion (c):   {perf['criterion']:.2f}",
        f"Mean RT (hits):  {rt_str}",
        "",
        "Hit rate by period:",
    ]
    for p in period_perf:
        lines.append(f"  Period {p['period']}:  {p['hit_rate']:.0%}")
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
    trials: list[dict],
    difficulty: str,
    block_clock: core.Clock,
) -> tuple[list[dict], bool]:
    """Returns (trials_with_outcomes, escaped)."""
    from psychopy import core, event, visual  # noqa: PLC0415

    isi_s = ISI_S[difficulty]

    stim_obj = visual.TextStim(win, text="", height=0.2, color="white", bold=True)
    feedback_obj = visual.TextStim(win, text="", height=0.07, pos=(0, -0.85), bold=True)

    for trial in trials:
        event.clearEvents()

        stim_obj.setPos(_jittered_pos(trial["quadrant"]))
        stim_obj.setText(trial["stimulus"])
        feedback_obj.setText("")

        responded = False
        rt_ms: Optional[float] = None
        response_t: Optional[float] = None
        trial_clock = core.Clock()

        # ── Stimulus on ───────────────────────────────────────
        stim_obj.draw()
        win.flip()
        trial_clock.reset()

        while trial_clock.getTime() < STIM_DURATION:
            t_now = trial_clock.getTime()
            for k, kt in event.getKeys(["space", "escape"], timeStamped=trial_clock):
                if k == "escape":
                    return trials, True
                if k == "space" and not responded:
                    rt_ms = kt * 1000
                    response_t = kt
                    responded = True
                    if trial["is_signal"]:
                        feedback_obj.setColor("green")
                        feedback_obj.setText("HIT")
                    else:
                        feedback_obj.setColor("red")
                        feedback_obj.setText("FALSE ALARM")

            stim_obj.draw()
            if responded and response_t is not None and (t_now - response_t) < FEEDBACK_DURATION:
                feedback_obj.draw()
            win.flip()

        # ── Blank / ISI ────────────────────────────────────────
        win.flip()
        isi_end = STIM_DURATION + isi_s

        while trial_clock.getTime() < isi_end:
            t_now = trial_clock.getTime()
            for k, kt in event.getKeys(["space", "escape"], timeStamped=trial_clock):
                if k == "escape":
                    return trials, True
                if k == "space" and not responded:
                    rt_ms = kt * 1000
                    response_t = kt
                    responded = True
                    if trial["is_signal"]:
                        feedback_obj.setColor("green")
                        feedback_obj.setText("HIT")
                    else:
                        feedback_obj.setColor("red")
                        feedback_obj.setText("FALSE ALARM")

            if responded and response_t is not None and (t_now - response_t) < FEEDBACK_DURATION:
                feedback_obj.draw()
            win.flip()

        # ── Record outcome ─────────────────────────────────────
        trial["time_on_watch_ms"] = round(block_clock.getTime() * 1000, 2)
        trial["response_made"] = responded
        trial["reaction_time_ms"] = round(rt_ms, 2) if rt_ms is not None else None
        if trial["is_signal"]:
            trial["outcome"] = "hit" if responded else "miss"
        else:
            trial["outcome"] = "false_alarm" if responded else "correct_rejection"

    return trials, False


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
    # where self.data (list) is indexed with a string key. With copyDict=True
    # that code path is skipped; results are read from dlg.dictionary instead.
    dlg = gui.DlgFromDict(
        info,
        title="CVT",
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

    trials = build_trial_sequence(difficulty, test_mode)

    win = _visual.Window(
        fullscr=True,
        color="black",
        units="norm",
        allowGUI=False,
    )
    block_clock = core.Clock()
    escaped = False

    try:
        if not _instructions(win, difficulty, test_mode):
            escaped = True
        else:
            block_clock.reset()
            trials, escaped = run_task(win, trials, difficulty, block_clock)
    finally:
        filename = save_data(participant_id, age, difficulty, test_mode, trials, timestamp)

    if not escaped:
        n_periods = NUM_PERIODS["test" if test_mode else "full"]
        _results_screen(win, trials, filename, n_periods)

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
