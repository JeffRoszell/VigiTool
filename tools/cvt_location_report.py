"""Central vs peripheral CVT measures, recomputed from saved session files.

Every CVT JSON stores each trial's location, outcome and reaction time, so the
central/peripheral split can be recomputed from data collected before the
`performance_by_location` block existed. Nothing is re-run and no file is
modified: this reads `trial_data` and writes one CSV.

    python tools/cvt_location_report.py                  # everything under data/
    python tools/cvt_location_report.py data/P001        # one participant
    python tools/cvt_location_report.py --by-period      # split by period too
    python tools/cvt_location_report.py -o report.csv

One row per participant x difficulty x location class ("total", "central",
"peripheral"), so the "total" rows reproduce the block-level numbers and the
other two split them. The measures come from `cvt_task`, the same code the
task itself uses, so the report and the JSON cannot drift apart.

Central is 1 of the 5 locations: a 20-signal block has ~4 central signals.
`n_signals` is in every row for that reason — read d_prime and criterion for
the central cell against it.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cvt_task import compute_sdt, location_class  # noqa: E402

FIELDS = (
    "participant_id", "difficulty", "timestamp", "period", "location_class",
    "n_signals", "n_nonsignals", "hits", "misses", "false_alarms",
    "correct_rejections", "hit_rate", "false_alarm_rate", "d_prime",
    "criterion", "mean_rt_hits_ms", "test_mode", "source_file",
)


def _row(meta: dict, trials: list[dict], cls: str, period, source: Path) -> dict:
    metrics = compute_sdt(trials)
    return {
        "participant_id": meta.get("participant_id"),
        "difficulty": meta.get("difficulty"),
        "timestamp": meta.get("timestamp"),
        "period": "all" if period is None else period,
        "location_class": cls,
        "n_signals": sum(1 for t in trials if t.get("is_signal")),
        "n_nonsignals": sum(1 for t in trials if not t.get("is_signal")),
        "test_mode": meta.get("test_mode"),
        "source_file": source.name,
        **{k: metrics[k] for k in (
            "hits", "misses", "false_alarms", "correct_rejections", "hit_rate",
            "false_alarm_rate", "d_prime", "criterion", "mean_rt_hits_ms",
        )},
    }


def rows_for_file(path: Path, by_period: bool = False) -> list[dict]:
    """Rows for one CVT JSON.

    Raises ValueError for a file whose trials carry no location — sessions
    recorded before the five-location protocol cannot be split this way.
    """
    data = json.loads(path.read_text())
    meta = data.get("metadata", {})
    trials = data.get("trial_data", [])
    if trials and any("location" not in t for t in trials):
        raise ValueError(
            "trials have no location — this file predates the five-location "
            "protocol and cannot be split central/peripheral"
        )

    groups: list[tuple[object, list[dict]]] = [(None, trials)]
    if by_period:
        periods = sorted({t.get("period") for t in trials if t.get("period") is not None})
        groups += [(p, [t for t in trials if t.get("period") == p]) for p in periods]

    rows = []
    for period, subset in groups:
        rows.append(_row(meta, subset, "total", period, path))
        for cls in ("central", "peripheral"):
            in_cls = [t for t in subset if location_class(t["location"]) == cls]
            rows.append(_row(meta, in_cls, cls, period, path))
    return rows


def find_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    # Skips the PVT and the display-check folder by name.
    return sorted(p for p in root.rglob("cvt_*.json") if p.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", default="data",
                        help="data folder, participant folder or single CVT JSON")
    parser.add_argument("-o", "--output", default=None,
                        help="CSV path (default: <path>/cvt_location_report.csv)")
    parser.add_argument("--by-period", action="store_true",
                        help="also emit one set of rows per period")
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.exists():
        parser.error(f"{root} does not exist")

    files = find_files(root)
    if not files:
        parser.error(f"no cvt_*.json files under {root}")

    rows: list[dict] = []
    skipped: list[str] = []
    for path in files:
        try:
            rows += rows_for_file(path, by_period=args.by_period)
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            skipped.append(f"{path}: {exc}")

    out = Path(args.output) if args.output else (
        (root if root.is_dir() else root.parent) / "cvt_location_report.csv"
    )
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(FIELDS))
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} rows from {len(files) - len(skipped)} file(s) -> {out}")  # noqa: T201
    for line in skipped:
        print(f"  skipped {line}")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
