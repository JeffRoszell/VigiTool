"""Tests for CVT trial generation and SDT metrics — no PsychoPy required."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cvt_task import (
    SIGNALS_PER_PERIOD,
    NUM_PERIODS,
    build_trial_sequence,
    compute_sdt,
    compute_period_metrics,
    _critical_signal,
    _non_signal,
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
    sigs = SIGNALS_PER_PERIOD[mode]

    # correct total signal count
    assert sum(t["is_signal"] for t in trials) == sigs * n_periods

    # period structure preserved — trials within each period appear consecutively
    # and each period contains exactly `sigs` signals
    for p in range(1, n_periods + 1):
        period_trials = [t for t in trials if t["period"] == p]
        assert len([t for t in period_trials if t["is_signal"]]) == sigs

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


def test_all_quadrants_valid():
    from cvt_task import QUADRANT_POS
    trials = build_trial_sequence("high", True)
    valid = set(QUADRANT_POS.keys())
    for t in trials:
        assert t["quadrant"] in valid


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
