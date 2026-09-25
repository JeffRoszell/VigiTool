"""Tests for tools/cvt_location_report.py — the post-hoc central/peripheral CSV.

The script exists so sessions recorded before `performance_by_location` can
still be split, so the contract under test is: rows computed from `trial_data`
alone, "total" rows that reproduce the file's own block-level numbers, and a
readable refusal for files that carry no per-trial location.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

import pytest
from cvt_location_report import FIELDS, find_files, main, rows_for_file


def _file(tmp_path: Path, trials: list[dict], name: str = "cvt_high_20260925_101500.json",
          performance: dict | None = None) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps({
        "metadata": {
            "participant_id": "P001", "task": "cvt", "difficulty": "high",
            "timestamp": "20260925_101500", "test_mode": False,
        },
        "performance": performance or {},
        "trial_data": trials,
    }))
    return path


def _trial(location, is_signal, outcome, rt=None, period=1):
    return {
        "location": location, "is_signal": is_signal, "outcome": outcome,
        "reaction_time_ms": rt, "period": period,
    }


TRIALS = [
    _trial("center", True, "hit", 500.0),
    _trial("center", True, "miss"),
    _trial("center", False, "correct_rejection"),
    _trial("upper_left", True, "hit", 400.0),
    _trial("lower_right", True, "hit", 420.0, period=2),
    _trial("upper_right", False, "false_alarm", 380.0, period=2),
    _trial("lower_left", False, "correct_rejection", period=2),
]


def test_one_row_per_location_class_plus_a_total(tmp_path):
    rows = rows_for_file(_file(tmp_path, TRIALS))
    assert [r["location_class"] for r in rows] == ["total", "central", "peripheral"]
    assert all(set(r) == set(FIELDS) for r in rows)
    assert all(r["participant_id"] == "P001" and r["difficulty"] == "high" for r in rows)


def test_split_rows_sum_to_the_total_row(tmp_path):
    total, central, peripheral = rows_for_file(_file(tmp_path, TRIALS))
    for key in ("hits", "misses", "false_alarms", "correct_rejections",
                "n_signals", "n_nonsignals"):
        assert central[key] + peripheral[key] == total[key], key
    assert central["mean_rt_hits_ms"] == 500.0
    assert peripheral["mean_rt_hits_ms"] == 410.0


def test_rows_come_from_trial_data_not_the_stored_summary(tmp_path):
    """Files written before the split existed have no stored per-location
    numbers, so everything must be recomputed from the trials."""
    path = _file(tmp_path, TRIALS, performance={"hits": 999})
    total = rows_for_file(path)[0]
    assert total["hits"] == 3


def test_by_period_adds_a_set_of_rows_per_period(tmp_path):
    rows = rows_for_file(_file(tmp_path, TRIALS), by_period=True)
    assert [r["period"] for r in rows] == ["all"] * 3 + [1] * 3 + [2] * 3
    period_two = {r["location_class"]: r for r in rows if r["period"] == 2}
    assert period_two["peripheral"]["hits"] == 1
    assert period_two["central"]["n_signals"] == 0


def test_a_file_without_locations_is_refused_with_a_readable_reason(tmp_path):
    older = [{"is_signal": True, "outcome": "hit", "reaction_time_ms": 400.0}]
    with pytest.raises(ValueError, match="five-location"):
        rows_for_file(_file(tmp_path, older))


def test_find_files_picks_up_cvt_files_only(tmp_path):
    (tmp_path / "P001").mkdir()
    wanted = _file(tmp_path / "P001", TRIALS)
    (tmp_path / "P001" / "pvt_20260925_101500.json").write_text("{}")
    assert find_files(tmp_path) == [wanted]


def test_main_writes_a_csv_and_skips_unusable_files(tmp_path, capsys):
    _file(tmp_path, TRIALS)
    _file(tmp_path, [{"is_signal": True, "outcome": "hit"}],
          name="cvt_low_20260925_102000.json")
    out = tmp_path / "report.csv"

    assert main([str(tmp_path), "-o", str(out)]) == 0

    with out.open() as fh:
        rows = list(csv.DictReader(fh))
    assert [r["location_class"] for r in rows] == ["total", "central", "peripheral"]
    assert "skipped" in capsys.readouterr().out


def test_per_location_adds_a_row_for_each_of_the_five_locations(tmp_path):
    rows = rows_for_file(_file(tmp_path, TRIALS), per_location=True)
    classes = [r["location_class"] for r in rows]
    assert classes[:3] == ["total", "central", "peripheral"]
    assert set(classes[3:]) == {
        "center", "upper_left", "upper_right", "lower_left", "lower_right",
    }
    per_loc = {r["location_class"]: r for r in rows[3:]}
    assert per_loc["center"]["hits"] == 1
    assert per_loc["center"]["n_signals"] == 2
    assert sum(int(per_loc[loc]["hits"]) for loc in per_loc) == int(rows[0]["hits"])


def test_per_location_is_off_by_default(tmp_path):
    assert len(rows_for_file(_file(tmp_path, TRIALS))) == 3
