"""Tests for CVT trial generation and SDT metrics — no PsychoPy required."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cvt_task import (
    NUM_PERIODS,
    SIGNALS_PER_PERIOD,
    STIM_POS,
    CvtMarkerEmitter,
    _critical_signal,
    _non_signal,
    build_practice_sequence,
    build_trial_sequence,
    compute_period_metrics,
    compute_sdt,
)


# ── Stimulus generation ────────────────────────────────────────────────────

def test_critical_signal_diff():
    for _ in range(200):
        s = _critical_signal()
        assert abs(int(s[0]) - int(s[1])) <= 1, f"bad signal: {s}"


def test_non_signal_diff():
    for _ in range(200):
        s = _non_signal()
        assert abs(int(s[0]) - int(s[1])) > 1, f"bad non-signal: {s}"


# ── Trial sequence structure ───────────────────────────────────────────────

def _check_sequence(difficulty: str, test_mode: bool) -> None:
    mode = "test" if test_mode else "full"
    trials = build_trial_sequence(difficulty, test_mode)
    n_periods = NUM_PERIODS[mode]

    # correct total signal count
    assert sum(t["is_signal"] for t in trials) == SIGNALS_PER_PERIOD * n_periods

    # period structure preserved — each period has SIGNALS_PER_PERIOD signals
    for p in range(1, n_periods + 1):
        period_trials = [t for t in trials if t["period"] == p]
        signals = [t for t in period_trials if t["is_signal"]]
        assert len(signals) == SIGNALS_PER_PERIOD, (
            f"period {p} has {len(signals)} signals, expected {SIGNALS_PER_PERIOD}"
        )

        # U3 invariant: each location holds exactly one critical signal per period
        locs = sorted(t["location"] for t in signals)
        assert locs == sorted(STIM_POS.keys()), (
            f"period {p} signal locations {locs} != all 5 locations"
        )

    # trial numbers are sequential from 1
    assert [t["trial_number"] for t in trials] == list(range(1, len(trials) + 1))

    # periods appear in non-decreasing order (period structure not shuffled)
    periods_in_order = [t["period"] for t in trials]
    assert periods_in_order == sorted(periods_in_order)


def test_sequence_full_high():
    _check_sequence("high", False)


def test_sequence_full_low():
    _check_sequence("low", False)


def test_sequence_test_high():
    _check_sequence("high", True)


def test_sequence_test_low():
    _check_sequence("low", True)


def test_all_locations_valid():
    trials = build_trial_sequence("high", True)
    valid = set(STIM_POS.keys())
    for t in trials:
        assert t["location"] in valid


def test_center_is_a_location():
    """U3 protocol: central display added as 5th location."""
    assert "center" in STIM_POS
    assert STIM_POS["center"] == (0.0, 0.0)
    assert len(STIM_POS) == 5


def test_signals_per_period_is_five():
    """SIGNALS_PER_PERIOD must equal the number of locations."""
    assert SIGNALS_PER_PERIOD == len(STIM_POS) == 5


# ── Practice sequence ──────────────────────────────────────────────────────

def test_practice_sequence_has_signals_in_each_location():
    trials = build_practice_sequence("low")
    signals = [t for t in trials if t["is_signal"]]
    assert len(signals) >= 1
    # practice covers all 5 locations once each (capped by available trials)
    locs = {t["location"] for t in signals}
    assert locs == set(STIM_POS.keys())


def test_practice_sequence_high_pace():
    trials = build_practice_sequence("high")
    assert len(trials) > 0
    for t in trials:
        assert t["location"] in STIM_POS
        assert t["stimulus"].isdigit() and len(t["stimulus"]) == 2


# ── SDT metrics ────────────────────────────────────────────────────────────

def _make_trials(hits, misses, fas, crs):
    trials = []
    for _ in range(hits):
        trials.append({"is_signal": True, "outcome": "hit", "reaction_time_ms": 300.0})
    for _ in range(misses):
        trials.append({"is_signal": True, "outcome": "miss", "reaction_time_ms": None})
    for _ in range(fas):
        trials.append({"is_signal": False, "outcome": "false_alarm", "reaction_time_ms": None})
    for _ in range(crs):
        trials.append({"is_signal": False, "outcome": "correct_rejection", "reaction_time_ms": None})
    return trials


def test_sdt_perfect_hit_rate():
    trials = _make_trials(hits=5, misses=0, fas=0, crs=100)
    m = compute_sdt(trials)
    assert m["hits"] == 5
    assert m["misses"] == 0
    assert m["false_alarms"] == 0
    assert m["d_prime"] > 2.0  # high sensitivity


def test_sdt_chance_performance():
    trials = _make_trials(hits=3, misses=2, fas=50, crs=50)
    m = compute_sdt(trials)
    assert isinstance(m["d_prime"], float)
    assert isinstance(m["criterion"], float)


def test_sdt_no_crashes_on_empty():
    m = compute_sdt([])
    assert m["hits"] == 0
    assert m["d_prime"] == 0.0


def test_period_metrics_count():
    trials = build_trial_sequence("high", True)
    for t in trials:
        t["outcome"] = "hit" if t["is_signal"] else "correct_rejection"
        t["reaction_time_ms"] = 300.0 if t["is_signal"] else None
    n = NUM_PERIODS["test"]
    pm = compute_period_metrics(trials, n)
    assert len(pm) == n
    for p in pm:
        assert "hit_rate" in p
        assert "d_prime" in p


# ── iMotions marker emitter (Layer 4) ─────────────────────────────────────


class _FakeMarkerClient:
    """Records every marker call so tests can assert sequence/content."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def discrete(self, name, description=""):
        self.calls.append(("discrete", name, description))

    def scene_start(self, name, description="", media="I"):
        self.calls.append(("scene_start", name, description, media))

    def scene_end(self, name):
        self.calls.append(("scene_end", name))


def test_emitter_default_is_noop():
    em = CvtMarkerEmitter()
    em.block_start("high")
    em.stim_onset({"is_signal": True, "trial_number": 1, "period": 1})
    em.response({"is_signal": True, "trial_number": 1}, rt_ms=200.0)
    em.stim_offset({"is_signal": True, "trial_number": 1, "period": 1})
    em.block_end("high")
    # Just check nothing raised; default client is a NoOpMarkerClient.


def test_emitter_block_pair():
    fake = _FakeMarkerClient()
    em = CvtMarkerEmitter(fake)
    em.block_start("high")
    em.block_end("high")
    assert fake.calls == [
        ("scene_start", "cvt_high_block", "", "I"),
        ("scene_end", "cvt_high_block"),
    ]


def test_emitter_practice_pair_per_difficulty():
    fake = _FakeMarkerClient()
    em = CvtMarkerEmitter(fake)
    em.practice_start("low")
    em.practice_end("low")
    em.practice_start("high")
    em.practice_end("high")
    assert fake.calls == [
        ("scene_start", "cvt_practice_low", "", "I"),
        ("scene_end", "cvt_practice_low"),
        ("scene_start", "cvt_practice_high", "", "I"),
        ("scene_end", "cvt_practice_high"),
    ]


def test_emitter_stim_onset_distinguishes_signal_kind():
    fake = _FakeMarkerClient()
    em = CvtMarkerEmitter(fake)
    em.stim_onset({"is_signal": True, "trial_number": 5, "period": 2})
    em.stim_onset({"is_signal": False, "trial_number": 6, "period": 2})
    assert fake.calls == [
        ("scene_start", "cvt_signal_stim", "trial=5,period=2", "I"),
        ("scene_start", "cvt_nonsignal_stim", "trial=6,period=2", "I"),
    ]


def test_emitter_stim_offset_matches_onset_name():
    fake = _FakeMarkerClient()
    em = CvtMarkerEmitter(fake)
    em.stim_offset({"is_signal": True, "trial_number": 5, "period": 2})
    em.stim_offset({"is_signal": False, "trial_number": 6, "period": 2})
    assert fake.calls == [
        ("scene_end", "cvt_signal_stim"),
        ("scene_end", "cvt_nonsignal_stim"),
    ]


def test_emitter_response_carries_rt_and_kind():
    fake = _FakeMarkerClient()
    em = CvtMarkerEmitter(fake)
    em.response({"is_signal": True, "trial_number": 7}, rt_ms=423.5)
    em.response({"is_signal": False, "trial_number": 8}, rt_ms=512.0)
    assert fake.calls == [
        ("discrete", "cvt_response", "rt=423.5,trial=7,kind=signal"),
        ("discrete", "cvt_response", "rt=512.0,trial=8,kind=nonsignal"),
    ]


def test_emitter_period_marker():
    fake = _FakeMarkerClient()
    em = CvtMarkerEmitter(fake)
    em.period(3)
    assert fake.calls == [("discrete", "cvt_period_3", "")]


# ── Schema regression ─────────────────────────────────────────────────────


def test_metadata_has_no_age_field(tmp_path, monkeypatch):
    """U3 protocol: age is collected on paper, never in the JSON."""
    import json

    from cvt_task import save_data

    monkeypatch.chdir(tmp_path)
    trials = build_trial_sequence("high", test_mode=True)
    for t in trials:
        t["outcome"] = "correct_rejection" if not t["is_signal"] else "miss"
    path = save_data("PTEST", "high", True, trials, "20260506_120000")
    data = json.loads(path.read_text())
    assert "age" not in data["metadata"]
    assert data["metadata"]["participant_id"] == "PTEST"
    assert data["trial_data"][0]["location"] in STIM_POS
