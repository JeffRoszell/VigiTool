"""CVT — Cognitive Vigilance Task (PsychoPy implementation, Phase 1)"""
from __future__ import annotations

import json
import math
import random
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from imotions_api import NoOpMarkerClient

if TYPE_CHECKING:
    from psychopy import core, visual  # type stubs only — not imported at runtime


# ── Constants ──────────────────────────────────────────────────────────────

STIM_DURATION = 1.0           # s
ISI_S = {"high": 0.5, "low": 1.5}
BLOCK_MINUTES = {"full": 24, "test": 2}
NUM_PERIODS = {"full": 4, "test": 2}
SIGNALS_PER_PERIOD = 5         # one per location — see STIM_POS
FEEDBACK_DURATION = 0.3        # s
PRACTICE_MINUTES_PER_DIFFICULTY = 2.5
PRACTICE_SIGNALS_PER_DIFFICULTY = 5   # ~2/min — denser than real task for learning
EXAMPLE_SIGNALS = ("45", "88", "32")  # shown on practice intro

# Stimulus positions in norm units, origin at screen centre.
# Five locations: 4 quadrants + central display (per U3 protocol).
STIM_POS = {
    "upper_left":  (-0.5,  0.5),
    "upper_right": ( 0.5,  0.5),
    "lower_left":  (-0.5, -0.5),
    "lower_right": ( 0.5, -0.5),
    "center":      ( 0.0,  0.0),
}
JITTER = 0.05   # ± norm units


# ── iMotions marker labels ─────────────────────────────────────────────────


class CvtMarkerEmitter:
    """Translates CVT events into iMotions marker calls.

    Owns the label-string contract for CVT. Tests exercise this class directly
    with a fake client; production wires a real EventReceivingAPI through.
    Per the PI decision (May 2026), labels distinguish signal vs non-signal
    trials and use scene_start/scene_end pairs for stimulus and block ranges.
    """

    def __init__(self, client: Any | None = None) -> None:
        self.client = client if client is not None else NoOpMarkerClient()

    def block_start(self, difficulty: str) -> None:
        self.client.scene_start(f"cvt_{difficulty}_block")

    def block_end(self, difficulty: str) -> None:
        self.client.scene_end(f"cvt_{difficulty}_block")

    def practice_start(self, difficulty: str) -> None:
        self.client.scene_start(f"cvt_practice_{difficulty}")

    def practice_end(self, difficulty: str) -> None:
        self.client.scene_end(f"cvt_practice_{difficulty}")

    def period(self, period_num: int) -> None:
        self.client.discrete(f"cvt_period_{period_num}")

    def stim_onset(self, trial: dict) -> None:
        kind = "signal" if trial["is_signal"] else "nonsignal"
        # Practice trials carry no "period" key — report period=0 for them.
        self.client.scene_start(
            f"cvt_{kind}_stim",
            f"trial={trial['trial_number']},period={trial.get('period', 0)}",
        )

    def stim_offset(self, trial: dict) -> None:
        kind = "signal" if trial["is_signal"] else "nonsignal"
        self.client.scene_end(f"cvt_{kind}_stim")

    def response(self, trial: dict, rt_ms: float) -> None:
        kind = "signal" if trial["is_signal"] else "nonsignal"
        self.client.discrete(
            "cvt_response",
            f"rt={rt_ms:.1f},trial={trial['trial_number']},kind={kind}",
        )

    # Per PI decision (June 2026, Jeff_questions_U2): every scored trial gets
    # a discrete outcome marker; misses and false alarms are labeled errors of
    # omission and commission so epochs can be selected directly in iMotions.
    _OUTCOME_MARKERS = {
        "hit": "cvt_hit",
        "miss": "cvt_error_omission",
        "false_alarm": "cvt_error_commission",
        "correct_rejection": "cvt_correct_rejection",
    }

    def outcome(self, trial: dict) -> None:
        name = self._OUTCOME_MARKERS.get(trial.get("outcome"))
        if name is None:
            return
        rt = trial.get("reaction_time_ms")
        rt_str = f"{rt:.1f}" if rt is not None else "none"
        self.client.discrete(
            name,
            f"outcome={trial['outcome']},trial={trial['trial_number']},"
            f"period={trial.get('period', 0)},rt={rt_str}",
        )


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
    """Pure function — no external deps, directly unit-testable.

    Per the U3 protocol, every period contains exactly SIGNALS_PER_PERIOD
    critical signals, one in each STIM_POS location. Non-signals get a
    uniformly-random location.
    """
    mode = "test" if test_mode else "full"
    trial_cycle = STIM_DURATION + ISI_S[difficulty]
    period_s = BLOCK_MINUTES[mode] * 60 / NUM_PERIODS[mode]
    trials_per_period = int(period_s / trial_cycle)
    locations = list(STIM_POS.keys())

    if trials_per_period < SIGNALS_PER_PERIOD:
        raise ValueError(
            f"period of {period_s:.0f}s holds only {trials_per_period} trials; "
            f"need at least {SIGNALS_PER_PERIOD}"
        )

    trials: list[dict] = []
    trial_num = 1

    for period in range(1, NUM_PERIODS[mode] + 1):
        slot_indices = random.sample(range(trials_per_period), SIGNALS_PER_PERIOD)
        slot_locations = random.sample(locations, len(locations))
        signal_slots = dict(zip(slot_indices, slot_locations))

        for i in range(trials_per_period):
            is_sig = i in signal_slots
            loc = signal_slots[i] if is_sig else random.choice(locations)
            trials.append({
                "trial_number": trial_num,
                "period": period,
                "stimulus": _critical_signal() if is_sig else _non_signal(),
                "is_signal": is_sig,
                "location": loc,
                "time_on_watch_ms": None,
                "response_made": False,
                "reaction_time_ms": None,
                "outcome": None,
            })
            trial_num += 1

    return trials


def build_practice_sequence(difficulty: str) -> list[dict]:
    """Practice trials over PRACTICE_MINUTES_PER_DIFFICULTY at the given pace.

    Signals are sparse but cover all five locations once each (so the
    participant sees a critical signal in every screen position at least
    once during practice).
    """
    trial_cycle = STIM_DURATION + ISI_S[difficulty]
    n_trials = max(
        PRACTICE_SIGNALS_PER_DIFFICULTY,
        int(PRACTICE_MINUTES_PER_DIFFICULTY * 60 / trial_cycle),
    )
    locations = list(STIM_POS.keys())
    n_signals = min(PRACTICE_SIGNALS_PER_DIFFICULTY, n_trials, len(locations))
    slot_indices = random.sample(range(n_trials), n_signals)
    slot_locations = random.sample(locations, n_signals)
    signal_slots = dict(zip(slot_indices, slot_locations))

    trials: list[dict] = []
    for i in range(n_trials):
        is_sig = i in signal_slots
        loc = signal_slots[i] if is_sig else random.choice(locations)
        trials.append({
            "trial_number": i + 1,
            "stimulus": _critical_signal() if is_sig else _non_signal(),
            "is_signal": is_sig,
            "location": loc,
        })
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
            "task": "cvt",
            "difficulty": difficulty,
            "timestamp": timestamp,
            "stimulus_duration_ms": int(STIM_DURATION * 1000),
            "isi_ms": int(ISI_S[difficulty] * 1000),
            "block_duration_minutes": BLOCK_MINUTES[mode],
            "total_signals": SIGNALS_PER_PERIOD * NUM_PERIODS[mode],
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

def _jittered_pos(location: str) -> tuple[float, float]:
    x, y = STIM_POS[location]
    return (
        x + random.uniform(-JITTER, JITTER),
        y + random.uniform(-JITTER, JITTER),
    )


def _instructions(
    win: visual.Window,
    difficulty: str,
    test_mode: bool,
    block_num: Optional[int] = None,
) -> bool:
    """Show pre-block instructions. Returns False if ESC pressed instead of SPACE."""
    from psychopy import event, visual  # noqa: PLC0415

    pace = "500 ms blank" if difficulty == "high" else "1500 ms blank"
    mins = BLOCK_MINUTES["test" if test_mode else "full"]
    mode_tag = " [TEST MODE]" if test_mode else ""
    block_tag = f"Block {block_num} — " if block_num else ""

    body = (
        f"COGNITIVE VIGILANCE TASK{mode_tag}\n\n"
        f"{block_tag}Difficulty: {difficulty.upper()}  ({pace} between stimuli)\n"
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


def _practice_intro(win: visual.Window) -> bool:
    """Practice intro: instructions + 3 example critical signals. Returns False on ESC."""
    from psychopy import event, visual  # noqa: PLC0415

    body = (
        "PRACTICE\n\n"
        "You will now practice the task for about 5 minutes total\n"
        "(2.5 min slow, 2.5 min fast).\n\n"
        "Press SPACEBAR only when the digit difference is 0 or ±1.\n"
        "Feedback will be shown after each trial.\n\n"
        "Examples of CRITICAL SIGNALS (press SPACEBAR for these):"
    )
    body_obj = visual.TextStim(
        win, text=body, height=0.055, wrapWidth=1.6,
        color="white", alignText="center", pos=(0, 0.45),
    )

    example_objs = []
    xs = (-0.4, 0.0, 0.4)
    for x, sig in zip(xs, EXAMPLE_SIGNALS):
        example_objs.append(
            visual.TextStim(win, text=sig, height=0.18, color="white",
                            bold=True, pos=(x, -0.05))
        )
        example_objs.append(
            visual.TextStim(win, text="YES", height=0.06, color="green",
                            bold=True, pos=(x, -0.25))
        )

    foot = visual.TextStim(
        win, text="Press SPACEBAR to begin practice.",
        height=0.06, color="white", pos=(0, -0.6),
    )

    body_obj.draw()
    for o in example_objs:
        o.draw()
    foot.draw()
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
        "BLOCK COMPLETE\n",
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
    lines += ["", f"Saved to: {filename}", "", "Press SPACEBAR to continue."]

    msg = visual.TextStim(
        win, text="\n".join(lines), height=0.055,
        wrapWidth=1.6, color="white", alignText="left",
    )
    msg.draw()
    win.flip()
    event.waitKeys(keyList=["space", "escape"])


# ── Core task loop ─────────────────────────────────────────────────────────

def run_task(
    win: visual.Window,
    trials: list[dict],
    difficulty: str,
    block_clock: core.Clock,
    show_all_feedback: bool = False,
    emitter: Optional[CvtMarkerEmitter] = None,
) -> tuple[list[dict], bool]:
    """Returns (trials_with_outcomes, escaped).

    If show_all_feedback is True (practice mode), feedback is shown for every
    trial outcome — HIT, FALSE ALARM, MISS, CORRECT REJECTION — in large font.
    Otherwise only HIT and FALSE ALARM are shown (real-task behaviour).
    """
    from psychopy import core, event, visual  # noqa: PLC0415

    if emitter is None:
        emitter = CvtMarkerEmitter()

    isi_s = ISI_S[difficulty]

    stim_obj = visual.TextStim(win, text="", height=0.2, color="white", bold=True)
    fixation_obj = visual.TextStim(
        win, text="+", height=0.1, color="white", bold=True, pos=(0, 0),
    )
    fb_height = 0.12 if show_all_feedback else 0.07
    fb_pos = (0, -0.4) if show_all_feedback else (0, -0.85)
    feedback_obj = visual.TextStim(
        win, text="", height=fb_height, pos=fb_pos, bold=True,
    )

    prev_period: Optional[int] = None

    for trial in trials:
        event.clearEvents()

        period_num = trial.get("period")
        if period_num is not None and period_num != prev_period:
            emitter.period(period_num)
            prev_period = period_num

        stim_obj.setPos(_jittered_pos(trial["location"]))
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
        emitter.stim_onset(trial)

        while trial_clock.getTime() < STIM_DURATION:
            t_now = trial_clock.getTime()
            for k, kt in event.getKeys(["space", "escape"], timeStamped=trial_clock):
                if k == "escape":
                    return trials, True
                if k == "space" and not responded:
                    rt_ms = kt * 1000
                    response_t = kt
                    responded = True
                    emitter.response(trial, rt_ms)
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

        emitter.stim_offset(trial)

        # ── Blank / ISI with fixation ──────────────────────────
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
                    emitter.response(trial, rt_ms)
                    if trial["is_signal"]:
                        feedback_obj.setColor("green")
                        feedback_obj.setText("HIT")
                    else:
                        feedback_obj.setColor("red")
                        feedback_obj.setText("FALSE ALARM")

            fixation_obj.draw()
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
        emitter.outcome(trial)

        # ── Practice-only: feedback for misses & correct rejections ──
        if show_all_feedback and not responded:
            if trial["outcome"] == "miss":
                feedback_obj.setColor("red")
                feedback_obj.setText("MISS")
            else:
                feedback_obj.setColor("white")
                feedback_obj.setText("CORRECT")
            fb_end = trial_clock.getTime() + FEEDBACK_DURATION * 2
            while trial_clock.getTime() < fb_end:
                for k in event.getKeys(["escape"]):
                    if k == "escape":
                        return trials, True
                fixation_obj.draw()
                feedback_obj.draw()
                win.flip()

    return trials, False


def run_practice(
    win: visual.Window,
    test_mode: bool = False,
    emitter: Optional[CvtMarkerEmitter] = None,
) -> bool:
    """Single practice session: low then high difficulty.

    Returns True if escaped, False on normal completion.
    """
    from psychopy import core  # noqa: PLC0415

    if emitter is None:
        emitter = CvtMarkerEmitter()

    if not _practice_intro(win):
        return True

    for difficulty in ("low", "high"):
        trials = build_practice_sequence(difficulty)
        # Practice is short — clock starts fresh per segment
        clk = core.Clock()
        clk.reset()
        emitter.practice_start(difficulty)
        try:
            _, escaped = run_task(
                win, trials, difficulty, clk,
                show_all_feedback=True, emitter=emitter,
            )
        finally:
            emitter.practice_end(difficulty)
        if escaped:
            return True
    return False


# ── Full session ───────────────────────────────────────────────────────────

def run_full_session(
    win: visual.Window,
    participant_id: str,
    difficulty_order: tuple[str, str],
    test_mode: bool,
    timestamp: str,
    *,
    skip_practice: bool = False,
    break_minutes: Optional[float] = None,
    marker_client: Any | None = None,
) -> bool:
    """Run a full CVT session: practice → block1 → break → block2.

    Returns True if escaped.
    """
    from psychopy import core  # noqa: PLC0415

    from session_utils import (  # noqa: PLC0415
        BREAK_MINUTES,
        recalibration_hold,
        timed_break,
    )

    emitter = CvtMarkerEmitter(marker_client)

    if not skip_practice and run_practice(win, test_mode=test_mode, emitter=emitter):
        return True

    n_periods = NUM_PERIODS["test" if test_mode else "full"]
    block_clock = core.Clock()

    for block_num, difficulty in enumerate(difficulty_order, start=1):
        if not _instructions(win, difficulty, test_mode, block_num=block_num):
            return True

        trials = build_trial_sequence(difficulty, test_mode)
        block_clock.reset()
        emitter.block_start(difficulty)
        try:
            trials, escaped = run_task(
                win, trials, difficulty, block_clock, emitter=emitter,
            )
        finally:
            emitter.block_end(difficulty)

        filename = save_data(participant_id, difficulty, test_mode, trials, timestamp)
        if escaped:
            return True

        _results_screen(win, trials, filename, n_periods)

        if block_num < len(difficulty_order):
            mins = break_minutes if break_minutes is not None else BREAK_MINUTES
            if not timed_break(win, minutes=mins, label="BREAK BETWEEN BLOCKS"):
                return True
            if not recalibration_hold(win, marker_client):
                return True

    return False


# ── Entry point ────────────────────────────────────────────────────────────

def main() -> None:
    from psychopy import core, gui  # noqa: PLC0415
    from psychopy import visual as _visual  # noqa: PLC0415

    info: dict = {
        "Participant ID": "",
        "Difficulty order": ["high → low", "low → high"],
        "Test mode": False,
    }
    # copyDict=True works around a bug in PsychoPy 2026.1.3 DlgFromDict.show()
    # where self.data (list) is indexed with a string key. With copyDict=True
    # that code path is skipped; results are read from dlg.dictionary instead.
    dlg = gui.DlgFromDict(
        info,
        title="CVT",
        order=["Participant ID", "Difficulty order", "Test mode"],
        sortKeys=False,
        copyDict=True,
    )
    if not dlg.OK:
        core.quit()

    result = dlg.dictionary
    participant_id = str(result["Participant ID"]).strip() or "unknown"
    order_str = str(result["Difficulty order"])
    test_mode = bool(result["Test mode"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    difficulty_order = ("high", "low") if order_str.startswith("high") else ("low", "high")

    win = _visual.Window(
        fullscr=True,
        color="black",
        units="norm",
        allowGUI=False,
    )

    try:
        run_full_session(win, participant_id, difficulty_order, test_mode, timestamp)
    finally:
        win.close()
        core.quit()


if __name__ == "__main__":
    main()
