"""Tests for PVT metrics — no PsychoPy required."""
import inspect
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cvt_task
import pvt_task
import run_session
from pvt_task import (
    BLOCK_MINUTES,
    FEEDBACK_DURATION,
    INTERVAL_CHOICES_MS,
    LAPSE_THRESHOLD_MS,
    NUM_PERIODS,
    SPEC_SOURCE,
    STIM_TIMEOUT,
    VALID_RT_MIN_MS,
    PvtMarkerEmitter,
    compute_metrics,
    compute_period_metrics,
    make_stimulus,
    period_seconds,
    sample_interval_ms,
    sample_interval_s,
)


class _FakeMarkerClient:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def discrete(self, name, description=""):
        self.calls.append(("discrete", name, description))

    def scene_start(self, name, description="", media="I"):
        self.calls.append(("scene_start", name, description, media))

    def scene_end(self, name):
        self.calls.append(("scene_end", name))


def _trial(rt_ms, response_type, lapse, period=1):
    return {
        "trial_number": 1,
        "period": period,
        "time_on_watch_s": 0.0,
        "foreperiod_ms": 2000.0,
        "reaction_time_ms": rt_ms,
        "response_type": response_type,
        "lapse": lapse,
    }


def _valid(rt_ms, period=1):
    return _trial(rt_ms, "valid", rt_ms > LAPSE_THRESHOLD_MS, period)


def _lapse(rt_ms, period=1):
    return _trial(rt_ms, "lapse", True, period)


def _anticipatory(period=1):
    return _trial(50.0, "anticipatory", False, period)


def _timeout(period=1):
    return _trial(None, "timeout", True, period)


# ── compute_metrics ────────────────────────────────────────────────────────

def test_basic_valid_responses():
    trials = [_valid(200), _valid(250), _valid(300)]
    m = compute_metrics(trials)
    assert m["total_trials"] == 3
    assert m["valid_responses"] == 3
    assert m["lapses"] == 0
    assert m["mean_rt_ms"] == 250.0


def test_lapse_counted():
    trials = [_valid(250), _lapse(600)]
    m = compute_metrics(trials)
    assert m["lapses"] == 1
    assert m["lapse_percentage"] == 50.0
    assert m["valid_responses"] == 1


def test_timeout_is_lapse():
    trials = [_timeout()]
    m = compute_metrics(trials)
    assert m["lapses"] == 1
    assert m["total_trials"] == 1
    assert m["valid_responses"] == 0


def test_anticipatory_combined():
    trials = [_anticipatory(), _valid(250)]
    m = compute_metrics(trials, pre_stim_anticipatory=3)
    assert m["anticipatory_responses"] == 4  # 1 post-stim + 3 pre-stim


def test_fastest_slowest_10pct():
    rts = list(range(100, 200, 10))  # 10 values: 100,110,...190
    trials = [_valid(rt) for rt in rts]
    m = compute_metrics(trials)
    assert m["fastest_10pct_mean_ms"] == 100.0
    assert m["slowest_10pct_mean_ms"] == 190.0


def test_reciprocal_rt():
    trials = [_valid(200), _valid(200)]
    m = compute_metrics(trials)
    assert abs(m["reciprocal_rt"] - 5.0) < 0.001  # 1000/200 = 5


def test_empty_trials():
    m = compute_metrics([])
    assert m["total_trials"] == 0
    assert m["valid_responses"] == 0
    assert m["mean_rt_ms"] is None


def test_no_valid_rts():
    trials = [_timeout(), _anticipatory()]
    m = compute_metrics(trials)
    assert m["mean_rt_ms"] is None
    assert m["lapses"] == 1


# ── compute_period_metrics ─────────────────────────────────────────────────

def test_period_metrics_structure():
    trials = [_valid(200, period=1), _valid(300, period=2)]
    pm = compute_period_metrics(trials, 2)
    assert len(pm) == 2
    assert pm[0]["period"] == 1
    assert pm[0]["mean_rt_ms"] == 200.0
    assert pm[1]["mean_rt_ms"] == 300.0


def test_period_metrics_empty_period():
    trials = [_valid(200, period=1)]
    pm = compute_period_metrics(trials, 2)
    assert pm[1]["mean_rt_ms"] is None
    assert pm[1]["lapses"] == 0


def test_period_lapse_count():
    trials = [_valid(250, period=1), _lapse(700, period=1), _valid(200, period=2)]
    pm = compute_period_metrics(trials, 2)
    assert pm[0]["lapses"] == 1
    assert pm[1]["lapses"] == 0


# ── constants sanity ───────────────────────────────────────────────────────

def test_thresholds():
    assert VALID_RT_MIN_MS == 100.0
    assert LAPSE_THRESHOLD_MS == 500.0


def test_period_counts():
    assert NUM_PERIODS["full"] == 4
    assert NUM_PERIODS["test"] == 2


# ── iMotions marker emitter (Layer 4) ─────────────────────────────────────


# ── Spec constants (Millisecond Inquisit PVT keyboard manual) ──────────────

def test_block_is_ten_minutes():
    """Manual: 'recommended minimum time is 600000ms => 10 min'."""
    assert BLOCK_MINUTES["full"] == 10
    assert BLOCK_MINUTES["full"] * 60 == 600  # seconds


def test_test_mode_block_unchanged():
    assert BLOCK_MINUTES["test"] == 2
    assert NUM_PERIODS["test"] == 2


def test_feedback_duration_follows_manual():
    """Manual: rtFeedbackDuration 500ms. Supersedes the earlier 1 s value."""
    assert FEEDBACK_DURATION == 0.5


def test_manual_silent_values_retained():
    """The manual does not specify these; the implemented values stand."""
    assert STIM_TIMEOUT == 30.0
    assert VALID_RT_MIN_MS == 100.0
    assert LAPSE_THRESHOLD_MS == 500.0


def test_spec_source_is_recorded():
    assert "Inquisit" in SPEC_SOURCE or "Millisecond" in SPEC_SOURCE


def test_difficulty_concept_is_gone():
    """The PVT has no difficulty conditions; high/low is CVT-only.

    ISI_S and FOREPERIOD_RANGE must not merely be unused — a lingering
    constant invites a future change to reinstate the double-counted gap.
    """
    assert not hasattr(pvt_task, "ISI_S")
    assert not hasattr(pvt_task, "FOREPERIOD_RANGE")


# ── Trial intervals ────────────────────────────────────────────────────────

def test_interval_choices_are_the_discrete_one_second_steps():
    """Manual: 'randomly chosen (with replacement) from 1000ms ... 10000ms'."""
    assert tuple(INTERVAL_CHOICES_MS) == (
        1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000,
    )
    assert all(isinstance(v, int) for v in INTERVAL_CHOICES_MS)


def test_sample_interval_draws_only_from_the_set():
    rng = random.Random(1234)
    draws = [sample_interval_ms(rng) for _ in range(5000)]
    assert set(draws) == set(INTERVAL_CHOICES_MS)  # with replacement, all seen
    assert all(d % 1000 == 0 for d in draws)       # never a continuous value


def test_sample_interval_seconds_matches_ms():
    rng = random.Random(99)
    s = sample_interval_s(rng)
    assert 1.0 <= s <= 10.0
    assert (s * 1000) % 1000 == 0


def test_sample_interval_is_deterministic_under_seed():
    a = [sample_interval_ms(random.Random(7)) for _ in range(3)]
    b = [sample_interval_ms(random.Random(7)) for _ in range(3)]
    assert a == b


# ── Period structure ───────────────────────────────────────────────────────

def test_period_seconds_full_is_150():
    """10 min / 4 periods = 2.5 min — the first non-integer period length.

    Guards against integer division silently dropping the last 2 minutes
    of every period.
    """
    assert period_seconds("full") == 150.0
    assert isinstance(period_seconds("full"), float)


def test_period_seconds_covers_the_whole_block():
    for mode in ("full", "test"):
        assert period_seconds(mode) * NUM_PERIODS[mode] == BLOCK_MINUTES[mode] * 60.0


# ── Guard: the CVT constants share these names but not these values ────────

def test_cvt_constants_are_untouched():
    """cvt_task and pvt_task both define BLOCK_MINUTES/NUM_PERIODS.

    Both now hold NUM_PERIODS['full'] == 4 while the period lengths differ
    (6 min vs 2.5 min), so a stray edit that crossed the modules would
    produce a duration error no count assertion could see.
    """
    assert cvt_task.BLOCK_MINUTES["full"] == 24
    assert cvt_task.NUM_PERIODS["full"] == 4
    assert cvt_task.ISI_S == {"high": 0.5, "low": 1.5}
    assert cvt_task.BLOCK_MINUTES["full"] != pvt_task.BLOCK_MINUTES["full"]


# ── Stimulus geometry ──────────────────────────────────────────────────────

class _FakeCircle:
    """Records construction kwargs so geometry is assertable without a display."""

    def __init__(self, win, **kwargs):
        self.win = win
        self.kwargs = kwargs


def test_stimulus_is_a_true_circle():
    """Regression: the target rendered as an ellipse.

    The window uses "norm" units, which are anisotropic on a widescreen. The
    stimulus must therefore pass its own isotropic units explicitly rather
    than inheriting the window's.
    """
    stim = make_stimulus(win=object(), factory=_FakeCircle)
    assert stim.kwargs["units"] == "height"
    assert stim.kwargs["radius"] == 0.05
    assert stim.kwargs["fillColor"] == "red"


def test_stimulus_diameter_is_ten_percent_of_screen_height():
    """Manual: 'the default is 10% of the vertical screen'."""
    assert pvt_task.STIM_CIRCLE.diameter == 0.10
    assert pvt_task.STIM_CIRCLE.units == "height"


def test_make_stimulus_needs_no_psychopy_when_given_a_factory():
    """The import must be lazy, or these tests cannot run in CI."""
    src = inspect.getsource(make_stimulus)
    assert "if factory is None:" in src


# ── Data schema v2 ─────────────────────────────────────────────────────────

def _saved(tmp_path, test_mode=False):
    path = pvt_task.save_data(
        participant_id="P001",
        test_mode=test_mode,
        trials=[_valid(300.0), _lapse(600.0)],
        pre_stim_anticipatory=1,
        timestamp="20260905_120000",
        data_root=tmp_path,
    )
    return path, json.loads(path.read_text())


def test_save_data_filename_carries_no_difficulty(tmp_path):
    path, _ = _saved(tmp_path)
    assert path.name == "pvt_20260905_120000.json"
    path_t, _ = _saved(tmp_path, test_mode=True)
    assert path_t.name == "pvt_test_20260905_120000.json"


def test_schema_v2_drops_difficulty_and_isi(tmp_path):
    """Dropped, not nulled — a null key invites a downstream difficulty column."""
    _, data = _saved(tmp_path)
    meta = data["metadata"]
    assert "difficulty" not in meta
    assert "isi_ms" not in meta
    assert "foreperiod_range_ms" not in meta


def test_schema_v2_is_self_describing(tmp_path):
    _, data = _saved(tmp_path)
    meta = data["metadata"]
    assert meta["schema_version"] == 2
    assert meta["spec_source"] == SPEC_SOURCE
    assert meta["block_duration_minutes"] == 10
    assert meta["num_periods"] == 4
    assert meta["period_seconds"] == 150.0
    assert meta["interval_choices_ms"] == list(INTERVAL_CHOICES_MS)
    assert meta["feedback_duration_ms"] == 500
    assert meta["stimulus"]["diameter"] == 0.10
    assert meta["stimulus"]["units"] == "height"
    # Windowed runs are not analysable; the flag lets analysis exclude them.
    assert meta["display"] == {"screen": 0, "fullscreen": True}


# ── Session wiring ─────────────────────────────────────────────────────────

def test_run_full_session_has_no_difficulty_order():
    params = inspect.signature(pvt_task.run_full_session).parameters
    assert "difficulty_order" not in params


def test_run_full_session_args_are_keyword_only():
    """A stale positional call must raise, not slide test_mode into the
    slot difficulty_order used to occupy."""
    params = inspect.signature(pvt_task.run_full_session).parameters
    for name in ("test_mode", "timestamp", "break_minutes", "marker_client"):
        assert params[name].kind is inspect.Parameter.KEYWORD_ONLY, name


def test_build_task_options_gives_difficulty_to_cvt_only():
    opts = run_session.build_task_options({"CVT difficulty order": "high → low"})
    assert opts["cvt"]["difficulty_order"] == ("high", "low")
    assert "difficulty_order" not in opts["pvt"]
    assert opts["pvt"] == {}


def test_build_task_options_parses_the_reverse_order():
    opts = run_session.build_task_options({"CVT difficulty order": "low → high"})
    assert opts["cvt"]["difficulty_order"] == ("low", "high")


def test_pvt_emitter_default_is_noop():
    em = PvtMarkerEmitter()
    em.block_start()
    em.period(1)
    em.stim_onset(1, 1)
    em.response(1, 287.0, "valid")
    em.stim_offset()
    em.block_end()
    # Nothing raised; default client is NoOpMarkerClient.


def test_pvt_emitter_block_pair():
    """One block, one label — supersedes pvt_high_block / pvt_low_block."""
    fake = _FakeMarkerClient()
    em = PvtMarkerEmitter(fake)
    em.block_start()
    em.block_end()
    assert fake.calls == [
        ("scene_start", "pvt_block", "", "I"),
        ("scene_end", "pvt_block"),
    ]


def test_pvt_emitter_block_takes_no_difficulty():
    """A stale call site must fail loudly, not emit a mislabelled scene."""
    em = PvtMarkerEmitter(_FakeMarkerClient())
    try:
        em.block_start("low")
    except TypeError:
        pass
    else:
        raise AssertionError("block_start still accepts a difficulty argument")


def test_pvt_emitter_period_marker():
    fake = _FakeMarkerClient()
    em = PvtMarkerEmitter(fake)
    em.period(4)
    assert fake.calls == [("discrete", "pvt_period_4", "")]


def test_pvt_emitter_stim_pair():
    fake = _FakeMarkerClient()
    em = PvtMarkerEmitter(fake)
    em.stim_onset(42, 3)
    em.stim_offset()
    assert fake.calls == [
        ("scene_start", "pvt_stim", "trial=42,period=3", "I"),
        ("scene_end", "pvt_stim"),
    ]


def test_pvt_emitter_response_valid():
    fake = _FakeMarkerClient()
    em = PvtMarkerEmitter(fake)
    em.response(7, 287.3, "valid")
    assert fake.calls == [
        ("discrete", "pvt_response", "rt=287.3,type=valid,trial=7"),
    ]


def test_pvt_emitter_response_lapse_and_anticipatory():
    fake = _FakeMarkerClient()
    em = PvtMarkerEmitter(fake)
    em.response(8, 612.0, "lapse")
    em.response(9, 80.0, "anticipatory")
    assert fake.calls == [
        ("discrete", "pvt_response", "rt=612.0,type=lapse,trial=8"),
        ("discrete", "pvt_response", "rt=80.0,type=anticipatory,trial=9"),
    ]


def test_pvt_emitter_response_timeout_has_no_rt():
    fake = _FakeMarkerClient()
    em = PvtMarkerEmitter(fake)
    em.response(10, None, "timeout")
    assert fake.calls == [
        ("discrete", "pvt_response", "rt=none,type=timeout,trial=10"),
    ]


def test_pvt_emitter_anticipatory_phase():
    """Pre-stimulus presses carry a commission-error marker alongside the
    anticipatory marker (PI decision, Jeff_questions_U2)."""
    fake = _FakeMarkerClient()
    em = PvtMarkerEmitter(fake)
    em.anticipatory("isi")
    em.anticipatory("foreperiod")
    assert fake.calls == [
        ("discrete", "pvt_anticipatory", "phase=isi"),
        ("discrete", "pvt_error_commission", "type=anticipatory,phase=isi"),
        ("discrete", "pvt_anticipatory", "phase=foreperiod"),
        ("discrete", "pvt_error_commission", "type=anticipatory,phase=foreperiod"),
    ]


def test_pvt_emitter_error_outcome_omission():
    fake = _FakeMarkerClient()
    em = PvtMarkerEmitter(fake)
    em.error_outcome(3, "lapse", 612.0)
    em.error_outcome(4, "timeout", None)
    assert fake.calls == [
        ("discrete", "pvt_error_omission", "type=lapse,rt=612.0,trial=3"),
        ("discrete", "pvt_error_omission", "type=timeout,rt=none,trial=4"),
    ]


def test_pvt_emitter_error_outcome_commission():
    fake = _FakeMarkerClient()
    em = PvtMarkerEmitter(fake)
    em.error_outcome(5, "anticipatory", 80.0)
    assert fake.calls == [
        ("discrete", "pvt_error_commission", "type=anticipatory,rt=80.0,trial=5"),
    ]


def test_pvt_emitter_error_outcome_valid_is_silent():
    fake = _FakeMarkerClient()
    em = PvtMarkerEmitter(fake)
    em.error_outcome(6, "valid", 250.0)
    assert fake.calls == []
