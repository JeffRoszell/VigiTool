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
- **Participant ID**: free-text field (e.g., "P001")
- **Age**: numeric field
- **Difficulty condition**: dropdown or radio — High / Low
- **Task order**: managed by experimenter (they choose which script to run first), but selectable at startup for logging purposes

### 1.3 Data Output
- Structured directory: `data/<participant_id>/`
- File naming: `<task>_<difficulty>_<YYYYMMDD_HHMMSS>.json`
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
- **Stimulus location**: Displayed in one of four screen quadrants (upper-left, upper-right, lower-left, lower-right), randomized with slight positional jitter

### 2.2 Timing
- **Stimulus duration**: 1000 ms
- **Blank screen ISI**:
  - High difficulty: 500 ms (trial cycle = 1500 ms, ~40 events/min)
  - Low difficulty: 1500 ms (trial cycle = 2500 ms, ~24 events/min)
- **Block duration**: 24 minutes per difficulty condition
- **Periods**: 4 periods of 6 minutes each

### 2.3 Signal Distribution
- **Total critical signals per block**: 20
- **Signals per period**: 5 (evenly distributed)
- **Signal placement**: Randomized within each period
- **Signal probability**:
  - High difficulty: ~0.021 (20 signals / ~960 total trials)
  - Low difficulty: ~0.035 (20 signals / ~576 total trials)

### 2.4 Practice Mode (Optional)
- Offered at startup via checkbox or prompt
- Shortened version of the real task (~5 minutes, per Claypoole procedure)
- Same stimulus types and timing as selected difficulty condition
- Practice data NOT saved to participant data directory (or saved separately with `_practice` suffix)
- Clear indication to participant that it is practice

### 2.5 Response Window
- Participant may respond at any time during the stimulus display (1000 ms) or during the subsequent ISI (500 or 1500 ms)
- Response after stimulus offset but before next stimulus = valid response for that trial

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
- **Stimulus**: Red circle appears at screen center (replacing or near fixation cross)
- **Response**: Press SPACEBAR as quickly as possible when red circle appears
- **This is a simple reaction time task** — every stimulus requires a response

### 3.2 Timing
- **Fixation cross displayed**: continuously between stimuli
- **Stimulus (red circle)**: displayed until participant responds (or timeout)
- **Blank screen ISI**:
  - High difficulty: 500 ms (between response and next fixation cross)
  - Low difficulty: 1500 ms (between response and next fixation cross)
- **Foreperiod** (fixation cross to red circle onset): randomized within a range — TBD, suggest 1–10 seconds (standard PVT range), **confirm with Dr. Poltavski**
- **Block duration**: 24 minutes per difficulty condition
- **Periods**: 4 periods of 6 minutes each

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
- **Period-level breakdown**: metrics per 6-minute period for time-on-task analysis

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
    ├── pvt_high_20260316_150000.json
    ├── pvt_low_20260316_153000.json
    └── (practice files if saved)
```

### 4.2 JSON Schema — CVT
```json
{
  "metadata": {
    "participant_id": "P001",
    "age": 22,
    "task": "cvt",
    "difficulty": "high",
    "timestamp": "20260316_140000",
    "stimulus_duration_ms": 1000,
    "isi_ms": 500,
    "block_duration_minutes": 24,
    "total_signals": 20,
    "is_practice": false
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
    {"period": 1, "hit_rate": 0.0, "fa_rate": 0.0, "d_prime": 0.0, "mean_rt_ms": 0.0}
  ],
  "trial_data": [
    {
      "trial_number": 1,
      "period": 1,
      "time_on_watch_ms": 0.0,
      "stimulus": "45",
      "is_signal": true,
      "quadrant": "upper_left",
      "response_made": true,
      "reaction_time_ms": 487.3,
      "outcome": "hit"
    }
  ]
}
```

### 4.3 JSON Schema — PVT
```json
{
  "metadata": {
    "participant_id": "P001",
    "age": 22,
    "task": "pvt",
    "difficulty": "high",
    "timestamp": "20260316_150000",
    "isi_ms": 500,
    "block_duration_minutes": 24,
    "foreperiod_range_ms": [1000, 10000],
    "is_practice": false
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

## 5. Between-Block Transition
- After completing one difficulty block, display: "Block complete. Press SPACEBAR when ready to continue."
- Experimenter manages break duration externally
- Log the break duration in the data (time between block end and spacebar press)

---

## 6. Open Items (Require Confirmation with Dr. Poltavski)
- [ ] PVT foreperiod range: Is 1–10 seconds correct, or a different range?
- [ ] PVT stimulus: Is the red circle a filled circle? What approximate size?
- [ ] Should the fixation cross remain visible during the foreperiod, or is there a blank interval?
- [ ] Event marker integration timeline and hardware specifics for B-Alert, Tobii, Smarteye
- [ ] Any specific counterbalancing scheme to encode (e.g., ABBA, Latin square)?
- [ ] Should the two difficulty blocks within a task always run in a specific order, or is order also counterbalanced?
