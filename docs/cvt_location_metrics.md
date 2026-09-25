# CVT measures by stimulus location

*Added September 2026, at Dr. Gupta's request following discussion with Dr. Poltavski.*

## What you asked for

Every CVT measure — hits, false alarms, d′, criterion, mean hit RT — reported
for the whole block, for central stimuli, and for peripheral stimuli, within
each difficulty condition.

## What counts as central

The CVT places each stimulus in one of five locations: four quadrants and the
centre of the screen.

- **Central** = `center`
- **Peripheral** = `upper_left`, `upper_right`, `lower_left`, `lower_right`

## Where the numbers are

Each CVT file covers one difficulty block, so high and low come out as
separate files: `cvt_high_<timestamp>.json` and `cvt_low_<timestamp>.json`.
Inside each file:

| Where | What it holds |
|---|---|
| `performance` | The whole block. Unchanged from before. |
| `performance_by_location.central` | The same measures, central stimuli only |
| `performance_by_location.peripheral` | The same measures, peripheral stimuli only |
| `period_performance[].by_location` | The same split, for each 6-minute period |

Each location block contains:

```json
{
  "hits": 3, "misses": 1, "false_alarms": 2, "correct_rejections": 186,
  "hit_rate": 0.7778, "false_alarm_rate": 0.0133,
  "d_prime": 2.98, "criterion": 0.71, "mean_rt_hits_ms": 486.2,
  "n_signals": 4, "n_nonsignals": 188
}
```

`n_signals` and `n_nonsignals` say how many trials each number rests on.

## How to read it

**Mean hit RT** is the measure that answers the question in your second
message, and it's on solid ground in both cells.

**d′ and criterion for the central cell need care.** Centre is 1 of 5
locations, so a 20-signal block contains about 4 central signals. The values
are computed and reported, with `n_signals` beside them, so the estimate is
never read without knowing what it rests on. Hit rate and false-alarm rate use
the log-linear correction (Hautus, 1995), so rates of 0 and 1 don't produce
infinite d′ — but 4 trials is still 4 trials. Aggregating across participants,
or across the two blocks, is the usual way to firm this up.

**Peripheral is roughly 16 signals per block**, four times the central count,
so the two cells are not equally precise. Comparing them directly is a
comparison of a stable estimate with a noisy one.

## Sessions already collected

Nothing needs re-running. Every session file already stores each trial's
location, outcome and reaction time, so the split can be rebuilt from data
collected before this change:

```bash
python tools/cvt_location_report.py                      # everything under data/
python tools/cvt_location_report.py data/P001            # one participant
python tools/cvt_location_report.py --by-period          # also split by period
python tools/cvt_location_report.py -o ~/Desktop/cvt.csv
```

This writes `cvt_location_report.csv`: one row per participant × difficulty ×
location class (`total`, `central`, `peripheral`), with the measures and the
trial counts as columns. It's ready to open in Excel, SPSS or R. Nothing is
modified — the script only reads.

The script recomputes from the raw trials rather than copying the stored
summary, so it gives the same answer for old and new files, and it uses the
task's own metric code, so the CSV and the JSON can't disagree.

Sessions recorded before the five-location protocol have no location on each
trial. Those files are listed as skipped, with the reason, instead of being
silently left out.

## Question outstanding

Would you like central d′ and criterion kept as they are (reported with their
trial counts), or would you rather d′ and criterion stayed at the block level,
with only hits, false alarms and mean RT split by location? Either is a small
change from here.
