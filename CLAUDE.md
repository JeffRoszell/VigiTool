# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vigilance task suite for cognitive neuroscience research at UND Psychology Department. Contains Python-based sustained attention tasks using tkinter (standard library only, no external dependencies).

### Tasks

- **Digit Vigilance Task** (`digit_vigilance_WORKING.py`): 24-minute sustained attention task based on Claypoole et al. (2019). Participants respond to two-digit numbers where digit difference is 0 or +/-1 (critical signals). Two difficulty conditions: high (500ms ISI) and low (1500ms ISI). Measures d', criterion, hit rate, false alarm rate, and vigilance decrement across 4 six-minute periods.
- **PVT** (`pvt_task_WORKING.py`): 10-minute Psychomotor Vigilance Task measuring simple reaction time to a millisecond counter appearing at random 1-10s intervals.

### Key Design Details

- All tasks use tkinter fullscreen with black background
- Keyboard input uses only lowercase `<space>` binding (compatibility fix for all tkinter versions 8.5-9.0)
- Both canvas and root bindings are set for keyboard events to ensure focus capture
- Data output is JSON with timestamped filenames (e.g., `digit_vigilance_high_YYYYMMDD_HHMMSS.json`)
- Signal detection theory metrics (d', criterion) use an approximate z-score function rather than scipy
- ESC key triggers emergency exit with data save

## Running Tasks

```bash
python3 digit_vigilance_WORKING.py
python3 pvt_task_WORKING.py
```

Or open in Spyder and press F5. User must click the black screen first to give it keyboard focus.

## Data Analysis

```bash
python3 analyze_data.py
```

Analyzes all `*.json` data files in the working directory.
