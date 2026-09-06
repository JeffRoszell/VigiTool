"""PVT — Psychomotor Vigilance Task (PsychoPy implementation, Phase 1)"""
from __future__ import annotations

import json
import random
import statistics
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, Optional

from imotions_api import NoOpMarkerClient

if TYPE_CHECKING:
    from psychopy import core, visual  # type stubs only — not imported at runtime


# ── Constants ──────────────────────────────────────────────────────────────

# The Millisecond Inquisit Perceptual Vigilance Task (keyboard) manual is the
# authoritative specification for this task (designated Sept 2026). Where the
# implementation and the manual disagree, the manual wins; where the manual is
# silent, the implemented value stands and is marked below.
SPEC_SOURCE = "Millisecond Inquisit Perceptual Vigilance Task (keyboard) manual"
SCHEMA_VERSION = 2

BLOCK_MINUTES = {"full": 10, "test": 2}  # manual: 600000 ms => 10 min
NUM_PERIODS = {"full": 4, "test": 2}     # manual silent — 4 for CVT comparability

# One interval per trial, drawn with replacement from the discrete 1-10 s set.
# There is NO separate post-response ISI: the manual defines a single gap
# between trials, and adding a blank-screen wait on top would double-count it.
INTERVAL_CHOICES_MS = tuple(range(1000, 10001, 1000))

FEEDBACK_DURATION = 0.5                  # s — manual: rtFeedbackDuration 500ms
STIM_TIMEOUT = 30.0                      # s — manual silent, retained
VALID_RT_MIN_MS = 100.0                  # < this = anticipatory; manual silent
LAPSE_THRESHOLD_MS = 500.0               # > this = lapse; manual silent


def sample_interval_ms(rng=random) -> int:
    """One inter-trial interval, drawn with replacement from the discrete set.

    `rng` is injectable so tests can seed it without touching global state.
    """
    return rng.choice(INTERVAL_CHOICES_MS)


def sample_interval_s(rng=random) -> float:
    return sample_interval_ms(rng) / 1000.0


def period_seconds(mode: str) -> float:
    """Length of one period, in seconds.

    Float division on purpose: full mode is 10/4 = 2.5 min, the first
    non-integer period length in this suite. Integer truncation here would
    silently drop the tail of every period.
    """
    return BLOCK_MINUTES[mode] * 60.0 / NUM_PERIODS[mode]


class CircleSpec(NamedTuple):
    """Geometry of the PVT target, as specified by the manual."""

    units: str
    radius: float
    fill_color: str
    line_color: str

    @property
    def diameter(self) -> float:
        return self.radius * 2.0


# "height" units are isotropic, so the target renders as a true circle at any
# aspect ratio. The window itself uses "norm" units, which are NOT isotropic on
# a widescreen — inheriting them is what made this stimulus an ellipse.
# Manual: diameter is 10% of the vertical screen.
STIM_CIRCLE = CircleSpec(
    units="height", radius=0.05, fill_color="red", line_color="red",
)


# ── iMotions marker labels ─────────────────────────────────────────────────


class PvtMarkerEmitter:
    """Translates PVT events into iMotions marker calls.

    Owns the label-string contract for PVT. Same construction pattern as
    CvtMarkerEmitter — tests exercise this directly with a fake client.
    """

    def __init__(self, client: Any | None = None) -> None:
        self.client = client if client is not None else NoOpMarkerClient()

    def block_start(self) -> None:
        """Scene start for the block.

        The PVT has a single block and no difficulty conditions, so the label
        carries neither. Supersedes pvt_high_block / pvt_low_block (Sept 2026)
        — iMotions epoch definitions keyed on the old labels will match
        nothing rather than erroring, so this rename needs coordination.
        """
        self.client.scene_start("pvt_block")

    def block_end(self) -> None:
        self.client.scene_end("pvt_block")

    def period(self, period_num: int) -> None:
        self.client.discrete(f"pvt_period_{period_num}")

    def stim_onset(self, trial_num: int, period: int) -> None:
        self.client.scene_start("pvt_stim", f"trial={trial_num},period={period}")

    def stim_offset(self) -> None:
        self.client.scene_end("pvt_stim")

    def response(
        self, trial_num: int, rt_ms: Optional[float], response_type: str
    ) -> None:
        rt_str = f"{rt_ms:.1f}" if rt_ms is not None else "none"
        self.client.discrete(
            "pvt_response",
            f"rt={rt_str},type={response_type},trial={trial_num}",
        )

    def anticipatory(self, phase: str = "foreperiod") -> None:
        """Press during the interval, before the stimulus appears.

        `phase` is retained at its historical "foreperiod" value for marker
        contract stability; the "isi" phase no longer occurs.

        Pre-stimulus presses are errors of commission (PI decision June 2026),
        so an error marker accompanies the existing anticipatory marker.
        """
        self.client.discrete("pvt_anticipatory", f"phase={phase}")
        self.client.discrete("pvt_error_commission", f"type=anticipatory,phase={phase}")

    # Per PI decision (June 2026, Jeff_questions_U2): label errors of omission
    # (lapses / timeouts) and commission (anticipatory presses) explicitly so
    # epochs can be selected directly in iMotions.
    def error_outcome(
        self, trial_num: int, response_type: str, rt_ms: Optional[float]
    ) -> None:
        if response_type in ("lapse", "timeout"):
            name = "pvt_error_omission"
        elif response_type == "anticipatory":
            name = "pvt_error_commission"
        else:
            return
        rt_str = f"{rt_ms:.1f}" if rt_ms is not None else "none"
        self.client.discrete(
            name, f"type={response_type},rt={rt_str},trial={trial_num}"
        )


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

DATA_ROOT = Path("data")

def save_data(
    participant_id: str,
    test_mode: bool,
    trials: list[dict],
    pre_stim_anticipatory: int,
    timestamp: str,
    eye_tracker: str | None = None,
    display: dict | None = None,
    data_root: Path | None = None,
) -> Path:
    """Write the session output. Schema v2 — see REQUIREMENTS §4.3.

    v2 drops `difficulty` and `isi_ms` entirely rather than nulling them: a
    null key invites downstream code to keep a difficulty column and mis-join
    PVT against CVT. An absent `schema_version` means v1, which is a
    *different protocol* and must not be pooled with v2 data.

    `data_root` exists so tests can write to a tmp directory.
    """
    mode = "test" if test_mode else "full"
    suffix = "_test" if test_mode else ""
    out_dir = (data_root or DATA_ROOT) / participant_id
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = out_dir / f"pvt{suffix}_{timestamp}.json"

    output = {
        "metadata": {
            "participant_id": participant_id,
            "task": "pvt",
            "timestamp": timestamp,
            "schema_version": SCHEMA_VERSION,
            "spec_source": SPEC_SOURCE,
            "block_duration_minutes": BLOCK_MINUTES[mode],
            "num_periods": NUM_PERIODS[mode],
            "period_seconds": period_seconds(mode),
            "interval_choices_ms": list(INTERVAL_CHOICES_MS),
            "feedback_duration_ms": int(FEEDBACK_DURATION * 1000),
            "stim_timeout_s": STIM_TIMEOUT,
            "lapse_threshold_ms": LAPSE_THRESHOLD_MS,
            "valid_rt_min_ms": VALID_RT_MIN_MS,
            "stimulus": {
                "shape": "circle",
                "units": STIM_CIRCLE.units,
                "diameter": STIM_CIRCLE.diameter,
                "color": STIM_CIRCLE.fill_color,
            },
            # Windowed runs can lose exclusive-fullscreen frame timing, so
            # this is recorded to let analysis exclude them.
            "display": display or {"screen": 0, "fullscreen": True},
            "is_practice": False,
            "test_mode": test_mode,
            "eye_tracker": eye_tracker,
        },
        "performance": compute_metrics(trials, pre_stim_anticipatory),
        "period_performance": compute_period_metrics(trials, NUM_PERIODS[mode]),
        "trial_data": trials,
    }

    with filename.open("w") as f:
        json.dump(output, f, indent=2)

    return filename


# ── PsychoPy display helpers ───────────────────────────────────────────────

def make_stimulus(win: visual.Window, factory=None):
    """Build the PVT target from STIM_CIRCLE.

    `units` is passed explicitly so the stimulus does not inherit the window's
    anisotropic "norm" units — that inheritance is what rendered this circle
    as an ellipse. `factory` is injectable so tests can assert the geometry
    without a display; it must be resolved inside the body, since a default
    argument would evaluate `visual` at import time and break headless runs.
    """
    if factory is None:
        from psychopy import visual  # noqa: PLC0415

        factory = visual.Circle
    return factory(
        win,
        units=STIM_CIRCLE.units,
        radius=STIM_CIRCLE.radius,
        fillColor=STIM_CIRCLE.fill_color,
        lineColor=STIM_CIRCLE.line_color,
    )


def _instructions(win: visual.Window, test_mode: bool) -> bool:
    """Returns False if ESC pressed instead of SPACE."""
    from psychopy import event, visual  # noqa: PLC0415

    mins = BLOCK_MINUTES["test" if test_mode else "full"]
    mode_tag = " [TEST MODE]" if test_mode else ""

    body = (
        f"PSYCHOMOTOR VIGILANCE TASK{mode_tag}\n\n"
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
    block_clock: core.Clock,
    n_periods: int,
    block_s: float,
    emitter: Optional[PvtMarkerEmitter] = None,
) -> tuple[list[dict], int, bool]:
    """Returns (trials, pre_stim_anticipatory_count, escaped)."""
    from psychopy import core, event, visual  # noqa: PLC0415

    if emitter is None:
        emitter = PvtMarkerEmitter()

    period_s = block_s / n_periods

    fixation = visual.TextStim(win, text="+", height=0.1, color="white", bold=True)
    circle = make_stimulus(win)
    feedback_obj = visual.TextStim(win, text="", height=0.08, pos=(0, -0.3), bold=True)
    too_early_obj = visual.TextStim(
        win, text="TOO EARLY", height=0.08, color="red", bold=True,
    )

    trials: list[dict] = []
    trial_num = 1
    pre_stim_anticipatory = 0
    prev_period: Optional[int] = None

    while block_clock.getTime() < block_s:

        # ── Fixation interval ──────────────────────────────
        # One gap per trial, drawn from the discrete set. There is no
        # separate blank-screen ISI before it — see INTERVAL_CHOICES_MS.
        foreperiod = sample_interval_s()
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
                    emitter.anticipatory()
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
        if period != prev_period:
            emitter.period(period)
            prev_period = period

        circle.draw()
        win.flip()
        emitter.stim_onset(trial_num, period)
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

        emitter.stim_offset()

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

        emitter.response(trial_num, rt_ms, response_type)
        emitter.error_outcome(trial_num, response_type, rt_ms)

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


# ── Full session ───────────────────────────────────────────────────────────

def run_full_session(
    win: visual.Window,
    participant_id: str,
    *,
    test_mode: bool,
    timestamp: str,
    break_minutes: Optional[float] = None,
    marker_client: Any | None = None,
    eye_tracker: str | None = None,
    display: Optional[dict] = None,
) -> bool:
    """Run a full PVT session: a single 10-minute block.

    There is no difficulty factor and therefore no second block, no
    within-task break, and no within-task recalibration hold. `break_minutes`
    is accepted and ignored so the session launcher can pass one uniform set
    of options to both tasks.

    Every parameter after `participant_id` is keyword-only: this signature
    previously took `difficulty_order` in third position, and making the rest
    keyword-only turns a stale positional call into a TypeError rather than a
    silently mis-parameterised session.

    Returns True if escaped.
    """
    from psychopy import core  # noqa: PLC0415

    emitter = PvtMarkerEmitter(marker_client)

    mode = "test" if test_mode else "full"
    n_periods = NUM_PERIODS[mode]
    block_s = BLOCK_MINUTES[mode] * 60.0
    block_clock = core.Clock()

    if not _instructions(win, test_mode):
        return True

    block_clock.reset()
    emitter.block_start()
    try:
        trials, pre_stim_anticipatory, escaped = run_task(
            win, block_clock, n_periods, block_s, emitter=emitter,
        )
    finally:
        emitter.block_end()

    filename = save_data(
        participant_id, test_mode,
        trials, pre_stim_anticipatory, timestamp,
        eye_tracker=eye_tracker,
        display=display,
    )
    if escaped:
        return True

    _results_screen(win, trials, pre_stim_anticipatory, filename, n_periods)
    return False


# ── Entry point ────────────────────────────────────────────────────────────

def main() -> None:
    from psychopy import core, gui  # noqa: PLC0415

    from session_utils import (  # noqa: PLC0415
        display_warning_body,
        make_window,
        message_screen,
        resolve_screen_index,
        screen_count,
    )

    info: dict = {
        "Participant ID": "",
        "Task display": list(range(1, screen_count() + 1)),
        "Fullscreen": True,
        "Test mode": False,
    }
    # copyDict=True works around a bug in PsychoPy 2026.1.3 DlgFromDict.show()
    dlg = gui.DlgFromDict(
        info,
        title="PVT",
        order=["Participant ID", "Task display", "Fullscreen", "Test mode"],
        sortKeys=False,
        copyDict=True,
    )
    if not dlg.OK:
        core.quit()

    result = dlg.dictionary
    participant_id = str(result["Participant ID"]).strip() or "unknown"
    test_mode = bool(result["Test mode"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    screen, fell_back = resolve_screen_index(int(result["Task display"]))
    fullscreen = bool(result["Fullscreen"])
    win = make_window(screen=screen, fullscr=fullscreen)

    try:
        if fell_back and not message_screen(win, display_warning_body(
            int(result["Task display"]),
        )):
            return
        run_full_session(
            win, participant_id, test_mode=test_mode, timestamp=timestamp,
            display={"screen": screen, "fullscreen": fullscreen},
        )
    finally:
        win.close()
        core.quit()


if __name__ == "__main__":
    main()
