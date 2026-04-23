# VigiTool

Vigilance task suite for IRB #0007078 — UND Psychology Department.

Compares sustained attention in younger adults (18–35) and older adults (65+) using concurrent EEG and eye-tracking (future phase). Built with [PsychoPy](https://www.psychopy.org/) for millisecond-accurate stimulus timing.

**PI:** Dr. Poltavski · **Co-PI:** Dr. Gupta · **Developer:** Jeff Roszell (BME)

---

## Tasks

### CVT — Cognitive Vigilance Task
Based on Claypoole et al. (2019). Two-digit numbers appear in screen quadrants; press **spacebar** when the difference between digits is 0 or ±1. Two difficulty conditions (high: 500 ms ISI, low: 1500 ms ISI). 24-minute blocks, 4 periods, 20 signals per block. Measures d′, criterion, hit rate, false alarm rate, and vigilance decrement.

### PVT — Psychomotor Vigilance Task
Fixation cross → red circle; press **spacebar** as fast as possible. Two 24-minute sessions (high: 500 ms ISI, low: 1500 ms ISI). Measures mean RT, lapses (RT > 500 ms), and anticipatory responses (RT < 100 ms).

---

## Lab Setup (first time only)

1. Install [Python 3.8+](https://www.python.org/downloads/)
2. Run the bootstrap script:
   ```
   python bootstrap.py
   ```
   This installs PsychoPy and all dependencies.

## Running the Tasks

```
python run.py
```

A launcher will appear — select CVT or PVT, choose difficulty, and enter the participant ID.

---

## Developer Setup

```bash
git clone https://github.com/JeffRoszell/VigiTool.git
cd VigiTool
pip install -e ".[dev]"

# Lint
ruff check src/ tests/

# Test
pytest tests/ -v
```

---

## Project Structure

```
VigiTool/
├── src/                    # Active PsychoPy implementation (in progress)
├── legacy/                 # Frozen original tkinter code — do not modify
├── tests/                  # pytest test suite
├── data/                   # Participant output (gitignored — IRB requirement)
├── Background/             # Reference papers and IRB documents
├── REQUIREMENTS.md         # Core task requirements
├── REQUIREMENTS_INTEGRATION.md  # EEG/eye-tracking integration (future)
├── MIGRATION_PLAN.md       # tkinter → PsychoPy migration roadmap
├── KNOWN_ISSUES.md         # Documented bugs in legacy code
└── QUESTIONS_FOR_PI.md     # Open protocol questions for Poltavski/Gupta
```

---

## Status

| Component | Status |
|-----------|--------|
| CVT (PsychoPy) | In progress |
| PVT (PsychoPy) | In progress |
| Unified launcher | Planned |
| iMotions integration | Planned (Phase 2) |
| EEG / eye-tracking | Planned (Phase 3) |

---

## Data

Participant data is saved to `data/<participant_id>/` as JSON and is **never committed to version control** per IRB #0007078 data handling requirements.
