"""Tests for PVT metrics — no PsychoPy required."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pvt_task import (
    LAPSE_THRESHOLD_MS,
    NUM_PERIODS,
    VALID_RT_MIN_MS,
    PvtMarkerEmitter,
    compute_metrics,
    compute_period_metrics,
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


def test_pvt_emitter_default_is_noop():
    em = PvtMarkerEmitter()
    em.block_start("high")
    em.period(1)
    em.stim_onset(1, 1)
    em.response(1, 287.0, "valid")
    em.stim_offset()
    em.block_end("high")
    # Nothing raised; default client is NoOpMarkerClient.


def test_pvt_emitter_block_pair():
    fake = _FakeMarkerClient()
    em = PvtMarkerEmitter(fake)
    em.block_start("low")
    em.block_end("low")
    assert fake.calls == [
        ("scene_start", "pvt_low_block", "", "I"),
        ("scene_end", "pvt_low_block"),
    ]


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
    fake = _FakeMarkerClient()
    em = PvtMarkerEmitter(fake)
    em.anticipatory("isi")
    em.anticipatory("foreperiod")
    assert fake.calls == [
        ("discrete", "pvt_anticipatory", "phase=isi"),
        ("discrete", "pvt_anticipatory", "phase=foreperiod"),
    ]
