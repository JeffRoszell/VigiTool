# Requirements Specification
## Vigilance Task Suite — Poltavski Lab, UND

### Study Reference
- **IRB**: #0007078
- **PI**: Dmitri Poltavski
- **Co-PI**: Dr. Utkarsh Gupta
- **Title**: Psychophysiological measures of Cognitive Performance in Younger and Older Adults During Vigilance Tasks
- **Task Design Based On**: Claypoole, Dever, Denues, & Szalma (2019). *The effects of event rate on a cognitive vigilance task.* Human Factors, 61(3), 440–450.

---

## 1. General Requirements

### 1.1 Platform & Technology
- Pure Python (3.7+), tkinter GUI
- No JavaScript, no web-based elements, no external Python packages beyond standard library
- Must run on Windows, macOS, and Linux
- Executable via command line (`python3 task.py`) or IDE (Spyder, etc.)

### 1.2 Participant Entry (GUI Dialog at Launch)
- **Participant ID**: free-text field — no forced format (per U3 protocol)
- **CVT difficulty order**: dropdown — `high → low` or `low → high` (counterbalancing managed by RAs externally). The PVT has no difficulty conditions (see §3).
- **Task display**: dropdown — which physical monitor the task runs on, 1-based (see §6)
- **Task order** (session launcher only): dropdown — `CVT → PVT` or `PVT → CVT`
- **No additional metadata** is collected in the application. Age group, session number, condition assignment, and experimenter initials are recorded on a paper questionnaire (per U3 protocol).

### 1.3 Data Output
- Structured directory: `data/<participant_id>/`
- File naming: `cvt_<difficulty>_<YYYYMMDD_HHMMSS>.json`, `pvt_<YYYYMMDD_HHMMSS>.json`
- JSON format with metadata, performance summary, and trial-level data
- Data saved relative to script location (configurable in future)
- Auto-save on completion, emergency save on ESC

### 1.4 Fullscreen Display
- Black background, white/colored stimuli
- Fullscreen on all platforms
- ESC exits with data save

### 1.5 Future Integration
- EEG and eye-tracking integration is planned as a separate development phase
- See `REQUIREMENTS_INTEGRATION.md` and `QUESTIONS_INTEGRATION.md` for details

---

## 2. Cognitive Vigilance Task (CVT)

### 2.1 Task Design (per Claypoole et al., 2019)
- **Stimulus type**: Two-digit numbers (e.g., "45", "73", "88")
- **Critical signals**: Digit difference is 0 or ±1 (e.g., 45→|4-5|=1, 88→|8-8|=0)
- **Non-signals**: Digit difference > 1 (e.g., 28→|2-8|=6)
- **Response**: Press SPACEBAR for critical signals only
- **Stimulus location**: One of five locations (upper-left, upper-right, lower-left, lower-right, center) — per U3 protocol, central display added to four quadrants. Randomized per trial with positional jitter to avoid order bias.

### 2.2 Timing
- **Stimulus duration**: 1000 ms
- **Blank screen ISI**:
  - High difficulty: 500 ms (trial cycle = 1500 ms, ~40 events/min)
  - Low difficulty: 1500 ms (trial cycle = 2500 ms, ~24 events/min)
- **Block duration**: 24 minutes per difficulty condition
- **Periods**: 4 periods of 6 minutes each

### 2.3 Signal Distribution
- **Total critical signals per block**: 20
- **Signals per period**: 5 — exactly one in each of the 5 locations (4 quadrants + center) per U3 protocol
- **Signal placement**: Temporally randomized within each period; spatial assignment fixed at one signal per location per period
- **Signal probability**:
  - High difficulty: ~0.021 (20 signals / ~960 total trials)
  - Low difficulty: ~0.035 (20 signals / ~576 total trials)

### 2.4 Practice Mode (Single Session at Start)
- One practice session at the very beginning of the experiment (per U3 protocol)
- 2.5 minutes at low difficulty, then 2.5 minutes at high difficulty (≈5 min total)
- Pre-practice intro shows on-screen instructions plus 3 example critical signals
- Live trials show large-font feedback for every outcome: HIT, FALSE ALARM, MISS, CORRECT
- Practice data is NOT saved to disk

### 2.5 Response Window
- Participant may respond at any time during the stimulus display (1000 ms) or during the subsequent ISI (500 or 1500 ms)
- Response after stimulus offset but before next stimulus = valid response for that trial
- A fixation cross (`+`) is shown at screen center throughout the ISI (per U3 protocol)

### 2.6 Performance Metrics
- **Hits**: Correct responses to critical signals
- **Misses**: Failed responses to critical signals
- **False alarms**: Responses to non-signals
- **Correct rejections**: No response to non-signals
- **Hit rate**: Hits / (Hits + Misses)
- **False alarm rate**: False Alarms / (False Alarms + Correct Rejections)
- **d' (sensitivity)**: Z(hit rate) - Z(false alarm rate)
- **Criterion (c)**: -0.5 × [Z(hit rate) + Z(false alarm rate)]
- **Mean RT for hits** (ms)
- **Period-level breakdown**: All above metrics computed per 6-minute period to measure vigilance decrement

### 2.7 Feedback During Task
- Brief visual feedback on response: "HIT" (green) or "FALSE ALARM" (red)
- Feedback disappears quickly (~300 ms) to not distract
- No feedback for correct rejections or misses (by design)

### 2.8 End-of-Task Display
- Performance summary: hits, misses, FA, d', criterion, mean RT
- Period-by-period hit rate table
- Filename where data was saved
- "Press ESC to exit" or "Press SPACEBAR to continue"

---

## 3. Psychomotor Vigilance Task (PVT)

### 3.1 Task Design (per IRB Protocol)
- **Fixation**: Fixation cross (+) displayed at screen center
- **Stimulus**: Filled red circle at screen center, replacing the fixation cross. Diameter is **10% of the vertical screen** (`units="height"`, radius 0.05) — the stimulus is sized in height units, not the window's `norm` units, so that it renders as a true circle on any aspect ratio
- **Response**: Press SPACEBAR as quickly as possible when red circle appears
- **This is a simple reaction time task** — every stimulus requires a response

### 3.2 Timing

Per the Millisecond Inquisit Perceptual Vigilance Task (keyboard) manual, designated
the authoritative PVT specification in September 2026.

- **Fixation cross displayed**: continuously between stimuli
- **Stimulus (red circle)**: displayed until participant responds (or timeout)
- **Interval** (fixation cross onset to red circle onset): drawn randomly **with replacement** from the discrete set {1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000} ms
- **No separate blank-screen ISI.** The manual defines a single interval between trials; the interval above *is* that entire gap. There is no additional post-response wait, and adding one would double-count the interval
- **Block duration**: 10 minutes (manual: "recommended minimum time is 600000ms")
- **Blocks**: one. The PVT has **no high/low difficulty conditions** — high/low remains a CVT-only factor
- **Periods**: 4 periods of 2.5 minutes each (see §3.5)
- **RT feedback**: displayed for 500 ms (manual `rtFeedbackDuration`)

### 3.3 Response Classification
- **Valid response**: RT between 100 ms and 500 ms
- **Lapse**: RT > 500 ms (attention failure)
- **Anticipatory response**: Pressing before the red circle appears, or RT < 100 ms
- **Timeout**: If no response within a defined window (e.g., 30 seconds), record as lapse and advance

### 3.4 Practice Mode (Optional)
- Short warm-up (~2 minutes or ~10 trials)
- Same structure as real task
- Practice data saved separately or not at all

### 3.5 Performance Metrics
- **Total trials / valid responses / anticipatory responses**
- **Mean, median, SD of RT** (valid responses only)
- **Min / Max RT**
- **Fastest 10% mean RT**
- **Slowest 10% mean RT**
- **Reciprocal RT**: mean of (1000/RT) for valid responses
- **Lapses**: count and percentage (RT > 500 ms)
- **Period-level breakdown**: metrics per 2.5-minute period for time-on-task analysis. Four periods are used (rather than two 5-minute periods) so that the vigilance decrement is described by a curve rather than a single difference score, and so period indices remain comparable with the CVT
- **Statistical note**: a 10-minute block yields roughly 95 trials (~24 per period), so period-level lapse counts are low-powered and descriptive. Block-level lapse rate is the primary metric. This reduced power is an accepted consequence of following the manual, not a defect

### 3.6 Feedback During Task
- Display RT in milliseconds after each valid response
- "TOO EARLY" for anticipatory responses
- Lapse indicator for slow responses (e.g., RT displayed in orange)

### 3.7 End-of-Task Display
- Performance summary: trial counts, mean/median RT, lapses, anticipatory
- Time-on-task analysis (first half vs second half)
- Filename where data was saved

---

## 4. Data Output Format

### 4.1 Directory Structure
```
data/
└── <participant_id>/
    ├── cvt_high_20260316_140000.json
    ├── cvt_low_20260316_143000.json
    ├── pvt_20260316_150000.json
    └── (practice files if saved)
```

### 4.2 JSON Schema — CVT
```json
{
  "metadata": {
    "participant_id": "P001",
    "task": "cvt",
    "difficulty": "high",
    "timestamp": "20260316_140000",
    "stimulus_duration_ms": 1000,
    "isi_ms": 500,
    "block_duration_minutes": 24,
    "total_signals": 20,
    "is_practice": false,
    "test_mode": false
  },
  "performance": {
    "hits": 0,
    "misses": 0,
    "false_alarms": 0,
    "correct_rejections": 0,
    "hit_rate": 0.0,
    "false_alarm_rate": 0.0,
    "d_prime": 0.0,
    "criterion": 0.0,
    "mean_rt_hits_ms": 0.0
  },
  "period_performance": [
    {"period": 1, "hit_rate": 0.0, "false_alarm_rate": 0.0, "d_prime": 0.0, "mean_rt_hits_ms": 0.0}
  ],
  "trial_data": [
    {
      "trial_number": 1,
      "period": 1,
      "time_on_watch_ms": 0.0,
      "stimulus": "45",
      "is_signal": true,
      "location": "upper_left",
      "response_made": true,
      "reaction_time_ms": 487.3,
      "outcome": "hit"
    }
  ]
}
```

`location` is one of: `upper_left`, `upper_right`, `lower_left`, `lower_right`, `center`. Additional locations may be added in future revisions.

### 4.3 JSON Schema — PVT
```json
{
  "metadata": {
    "participant_id": "P001",
    "task": "pvt",
    "timestamp": "20260316_150000",
    "schema_version": 2,
    "spec_source": "Millisecond Inquisit Perceptual Vigilance Task (keyboard) manual",
    "block_duration_minutes": 10,
    "num_periods": 4,
    "period_seconds": 150.0,
    "interval_choices_ms": [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000],
    "feedback_duration_ms": 500,
    "stim_timeout_s": 30.0,
    "lapse_threshold_ms": 500.0,
    "valid_rt_min_ms": 100.0,
    "stimulus": {"shape": "circle", "units": "height", "diameter": 0.10, "color": "red"},
    "display": {"screen": 0, "fullscreen": true},
    "is_practice": false,
    "test_mode": false
  },
  "performance": {
    "total_trials": 0,
    "valid_responses": 0,
    "anticipatory_responses": 0,
    "mean_rt_ms": 0.0,
    "median_rt_ms": 0.0,
    "std_rt_ms": 0.0,
    "min_rt_ms": 0.0,
    "max_rt_ms": 0.0,
    "fastest_10pct_mean_ms": 0.0,
    "slowest_10pct_mean_ms": 0.0,
    "reciprocal_rt": 0.0,
    "lapses": 0,
    "lapse_percentage": 0.0
  },
  "period_performance": [
    {"period": 1, "mean_rt_ms": 0.0, "median_rt_ms": 0.0, "lapses": 0}
  ],
  "trial_data": [
    {
      "trial_number": 1,
      "period": 1,
      "time_on_watch_s": 0.0,
      "foreperiod_ms": 3500,
      "reaction_time_ms": 267.4,
      "response_type": "valid",
      "lapse": false
    }
  ]
}
```

---

## 5. Between-Block and Between-Task Transitions
- **Between difficulty blocks within a task**: enforced timed 5-minute break with on-screen countdown (per U3 protocol). ESC aborts. Applies to the **CVT only** — the PVT is a single block and has no within-task break, and therefore no within-task recalibration hold.
- **Between tasks (CVT → PVT or PVT → CVT)**: enforced timed 5-minute break with on-screen countdown when launched via `run_session.py`.
- Per-block results screen is shown after each block; advances on SPACEBAR.
- **EEG baseline** is recorded once at the start of the session, before the first task. The session launcher displays an EEG-baseline hold screen for the experimenter to confirm before continuing.

---

## 6. Display Configuration

Added September 2026 after the first independent lab run, in which the task had to be
run with the second monitor physically disconnected because the fullscreen window
captured the cursor. The iMotions recording consequently ran unmonitored for the whole
session.

- **Task display**: the launch dialog offers a **1-based** display selection (RAs think
  "Display 2"), converted once at the dialog boundary to PsychoPy's 0-based `screen`
  index. Default is display 1.
- **Goal state**: the task runs fullscreen on the participant monitor while the RA
  retains a usable cursor on the operator monitor to monitor the iMotions recording
  live.
- **Fullscreen**: on by default. A windowed option is provided as an escape hatch when
  displays are mirrored or the index is wrong.
- **Pre-flight**: if the requested display index exceeds the detected screen count, the
  app warns on screen and falls back to display 1 rather than crashing or silently
  landing on the wrong monitor. Display indices come from the OS and can reorder when a
  monitor is unplugged or over remote desktop, so the index is confirmed before the
  participant is seated.
- **Analysability**: `screen` and `fullscreen` are recorded in the output metadata.
  Windowed mode can lose exclusive-fullscreen vsync and gain frame-timing jitter, so
  windowed runs are for monitoring and debugging only and are **not analysable**; the
  recorded flag lets analysis exclude them.

---

## 7. Open Items (Require Confirmation with Dr. Poltavski)
- [x] ~~PVT foreperiod range~~ — resolved Sept 2026: discrete 1–10 s draw per the Inquisit manual
- [x] ~~PVT stimulus size/fill~~ — resolved Sept 2026: filled red circle, diameter 10% of screen height, per the manual
- [x] ~~Fixation cross visibility during the foreperiod~~ — resolved: cross remains visible, replaced by the circle at onset
- [ ] PVT RT feedback duration: the manual specifies 500 ms; a June 2026 decision set 1 s. Manual applied under the tie-breaker rule — **confirm this was not a deliberate deviation**
- [ ] PVT period structure: the manual is silent. 4 × 2.5 min adopted provisionally for comparability with the CVT — **confirm with Dr. Gupta**
- [ ] Session duration under IRB #0007078: the PVT drops from ~48 min (two blocks plus break) to 10 min, changing the stated participant time commitment — **confirm whether a protocol modification must be filed**
- [ ] Event marker integration timeline and hardware specifics for B-Alert, Tobii, Smarteye
- [ ] Any specific counterbalancing scheme to encode (e.g., ABBA, Latin square)?
- [ ] Should the two CVT difficulty blocks always run in a specific order, or is order also counterbalanced?
