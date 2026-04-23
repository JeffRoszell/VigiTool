# Migration Plan: tkinter → PsychoPy + iMotions

## Overview

Migrate the vigilance task suite (CVT and PVT) from tkinter to PsychoPy, with iMotions integration for synchronized biosensor data collection (Smart Eye, Tobii Pro Fusion, B-Alert X-24 EEG).

## Why Migrate

- **Precise timing** — PsychoPy provides millisecond-accurate stimulus presentation; tkinter's `after()` is unreliable for RT measurement
- **Built-in SDT metrics** — eliminates the broken z-score approximation currently in the code
- **Native Tobii support** — PsychoPy has built-in eye-tracker integration via iohub
- **iMotions API** — simple TCP markers synchronize all biosensors without importing separate SDKs
- **Fixes most known bugs** — trial sequencing, timing, and metric calculation issues (see KNOWN_ISSUES.md) are handled by PsychoPy's experiment framework
- **No added cost** — PsychoPy is free and open source; iMotions is already available in the lab
- **Pure Python** — no JavaScript required

## Requirements

### Software (on each lab machine)
- Python 3.8+
- PsychoPy (`pip install psychopy`)
- iMotions (already installed)

### iMotions Configuration
- Global Preferences → API → Enable event reception
- Global Preferences → API → Use TCP (port 8089)

## Architecture

```
┌─────────────────────────────────┐
│         PsychoPy Task           │
│  (CVT or PVT Python script)     │
│                                 │
│  • Stimulus presentation        │
│  • Response collection          │
│  • Trial sequencing             │
│  • Data logging (local JSON)    │
│  • Sends TCP event markers ─────────┐
└─────────────────────────────────┘    │
                                       ▼
                              ┌──────────────┐
                              │   iMotions    │
                              │  (TCP :8089)  │
                              │              │
                              │  Receives     │
                              │  markers and  │
                              │  syncs with:  │
                              │  • Smart Eye  │
                              │  • Tobii Pro  │
                              │  • B-Alert    │
                              └──────────────┘
```

## Migration Phases

### Phase 1: Core Task Migration ✓ COMPLETE

Rewrite CVT and PVT using PsychoPy's experiment framework.

**CVT (Cognitive Vigilance Task)**
- Replace tkinter window with PsychoPy `visual.Window`
- Use `visual.TextStim` for digit display in quadrants
- Use PsychoPy `event` module for keyboard input
- Use PsychoPy `core.Clock` for precise timing (replaces `time.time()`)
- Implement proper trial sequencing with `data.TrialHandler` — fixes the shuffle-destroys-periods bug
- Use PsychoPy's built-in signal detection functions or implement correct Abramowitz & Stegun z-score
- Generate trial list with period structure preserved
- Maintain same parameters: 24-min blocks, 4 periods, 20 signals, 500ms/1500ms ISI

**PVT (Psychomotor Vigilance Task)**
- Replace tkinter with PsychoPy `visual.Window`
- Use `visual.TextStim` for RT counter display
- Use `core.Clock` for precise RT measurement
- Add difficulty selection (high/low) — currently missing
- Fix duration to 24 minutes per protocol
- Fix ISI to 500ms/1500ms per difficulty — not random 1-10s
- Implement proper anticipatory response handling without race conditions

**Both Tasks**
- Participant ID input dialog at launch (PsychoPy `gui.DlgFromDict`)
- Data saves to `data/<participant_id>/` with correct naming convention
- ESC triggers immediate emergency exit with data save (no confirmation dialog)
- Remove all debug print statements and labels

### Phase 2: iMotions Integration (next)

Add TCP event marker communication to both tasks.

**Connection Setup**
- Open TCP socket to `localhost:8089` at task start
- Graceful handling if iMotions is not running (log warning, continue without markers)

**Event Markers to Send**
- `task_start` — beginning of block
- `period_N_start` — start of each 6-minute period (N = 1–4)
- `stimulus_onset` — each stimulus appears (include trial type: signal/non-signal)
- `response` — participant presses spacebar (include RT)
- `task_end` — block complete
- `emergency_exit` — ESC pressed

**Marker Format**
```
Discrete:  M;2;;;stimulus_onset;;S;I\r\n
Range:     M;2;;;period_1;;S;I\r\n  ...  M;2;;;period_1;;E;I\r\n
```

**Marker Utility Module**
- Single `imotions_markers.py` module used by both tasks
- Connect, send discrete marker, send range marker start/end, disconnect
- Timestamps logged locally alongside marker sends for verification

### Phase 3: Validation

Verify the migrated tasks match protocol requirements before lab use.

**Timing Validation**
- Measure actual stimulus duration and ISI with PsychoPy's frame-level logging
- Confirm RT measurement accuracy against known input delays
- Verify 24-minute block duration

**Data Validation**
- Compare trial counts, signal distribution, and period structure against requirements
- Verify SDT metrics (d', criterion) against manual calculation
- Confirm JSON output matches schema in REQUIREMENTS.md

**iMotions Validation**
- Confirm markers appear in iMotions timeline at correct times
- Verify marker alignment with Smart Eye, Tobii, and B-Alert data streams
- Test emergency exit sends markers and saves data cleanly

**Cross-Platform**
- Test on Windows (primary lab OS), macOS, Linux
- Verify fullscreen, keyboard input, and focus behavior on each

### Phase 4: Data Analysis Update

Update `analyze_data.py` to work with the new setup.

- Remove hardcoded `/mnt/user-data/outputs` path
- Point to `data/<participant_id>/` directory
- Add iMotions marker log cross-reference if applicable
- Keep analysis logic the same (just fix the input paths)

## File Structure After Migration

```
PsychDept/
├── src/
│   ├── cvt_task.py              # CVT in PsychoPy
│   ├── pvt_task.py              # PVT in PsychoPy
│   ├── imotions_markers.py      # iMotions TCP marker utility
│   └── analyze_data.py          # Updated analysis script
├── legacy/                       # Frozen original code (unchanged)
├── data/                         # Participant output (gitignored)
├── tests/                        # Updated tests
└── ...
```

## Open Questions (Resolve Before Starting)

1. Which version of iMotions is installed in the lab?
2. Which version of Smart Eye Pro is installed?
3. Does the lab machine have Python installed, and what version?
4. Does Poltavski approve switching from tkinter to PsychoPy?
5. What is Smart Eye's specific role — does it need discrete event markers, or just time alignment in post-processing?
6. Will both tasks run on the same machine as iMotions, or separate machines?
7. Are there any other iMotions API consumers that might conflict on port 8089?
