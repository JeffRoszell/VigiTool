# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vigilance task suite for IRB #0007078 (PI: Poltavski, Co-PI: Gupta) at UND Psychology Department. Compares sustained attention in younger (18-35) and older (65+) adults using two tasks with concurrent EEG and eye-tracking (Smarteye) synchronized through iMotions.

**Lead Developer**: Jeff Roszell (BME master's student)

## Constraints

- **Pure Python 3.8+** with PsychoPy — no JavaScript, no web frameworks
- **Cross-platform**: must work on Windows, macOS, and Linux
- Dev dependencies (pytest, ruff) are acceptable but not required at runtime
- Participant data must never be committed to version control (IRB requirement)

## Project Structure

```
PsychDept/
├── src/                    # Active development
├── legacy/                 # Frozen original code — do not modify
├── tests/                  # pytest test suite
├── data/                   # Participant output (gitignored)
├── Background/             # Reference papers, IRB, legacy zip
├── .claude/agents/         # Custom agents (sme, compliance, e2e-test)
├── .github/workflows/      # CI pipeline
├── REQUIREMENTS.md          # Core task requirements
├── REQUIREMENTS_INTEGRATION.md  # EEG/eye-tracking integration (implemented)
├── QUESTIONS_FOR_PI.md      # Open questions for Poltavski/Gupta
└── QUESTIONS_INTEGRATION.md # Open questions for hardware integration
```

## Tasks

### CVT (Cognitive Vigilance Task)
Based on Claypoole et al. (2019). Two-digit numbers in screen quadrants; press spacebar when digit difference is 0 or ±1. Two difficulty conditions via event rate: high (500ms ISI, ~40/min) and low (1500ms ISI, ~24/min). 24-minute blocks, 4 periods, 20 signals per block. Measures d', criterion, hit rate, FA rate, vigilance decrement.

### PVT (Psychomotor Vigilance Task)
Fixation cross → red circle; press spacebar as fast as possible. Single 10-minute block, **no difficulty conditions** (high/low is CVT-only). Intervals drawn with replacement from the discrete {1000…10000} ms set — there is no separate blank-screen ISI. Filled red circle at 10% of screen height, RT feedback 500ms, 4 periods of 2.5 minutes. Measures RT, lapses (>500ms), anticipatory responses (<100ms).

Specified by the Millisecond Inquisit Perceptual Vigilance Task (keyboard) manual, authoritative as of September 2026: where the implementation and the manual disagree, the manual wins; where the manual is silent, the existing value stands.

## Development Commands

```bash
# Lint
ruff check src/ tests/

# Test
pytest tests/ -v

# Install dev dependencies
pip install -e ".[dev]"
```

## Custom Agents

- **`sme`** — Subject matter expert on vigilance tasks, SDT, Claypoole methodology, and the IRB protocol. Prefers local materials (Background/ folder); only web-searches when explicitly asked. Use for validating task parameters and methodology questions.
- **`compliance`** — Checks for PII, participant data in commits, .gitignore integrity, and IRB data handling. Use before commits or when reviewing data-handling code.
- **`e2e-test`** — Headless end-to-end regression test runner. Validates trial generation, metrics calculation, and JSON output schema without launching PsychoPy. Use after significant changes to task logic.

## Pre-Commit Hooks

Configured in `.claude/settings.json`:
1. Ruff lint check on src/ and tests/
2. Debug print() detection in src/
3. Participant data / IRB file commit blocking
4. Hardcoded path detection
5. Unit test execution

## Data Output

Participant data saves to `data/<participant_id>/` as `cvt_<difficulty>_<YYYYMMDD_HHMMSS>.json` and `pvt_<YYYYMMDD_HHMMSS>.json` — the PVT name carries no difficulty. PVT output is **schema v2**: no `difficulty` or `isi_ms`, plus `schema_version`, `spec_source` and the full parameter set so files are self-describing. An absent `schema_version` means v1, which is a *different protocol* and must not be pooled with v2 data. See REQUIREMENTS.md for the full JSON schema.

## Key Technical Notes

- UI and stimulus presentation use PsychoPy (`visual.Window`, `visual.TextStim`, `event`, `core.Clock`)
- SDT metrics use correct Abramowitz & Stegun z-score approximation
- ESC key triggers emergency exit with data save
- CVT timing: ISI controls event rate (500ms = high difficulty, 1500ms = low difficulty), stimulus duration is 1000ms
- PVT timing: one interval per trial, drawn with replacement from {1000…10000} ms. Do not add a post-response ISI on top of it — the manual defines a single gap, and summing the two would silently double-count it
- The PVT target must be built in `height` units, not the window's `norm` units: norm units are anisotropic on a widescreen, which is what made the circle render as an ellipse
- `cvt_task` and `pvt_task` both define `ISI_S`/`BLOCK_MINUTES`/`NUM_PERIODS`-style constants with the same names but different values. Both now hold `NUM_PERIODS["full"] == 4` while the periods are 6 min and 2.5 min respectively, so cross-contamination produces a duration error no count assertion can catch
- iMotions integration implemented: TCP markers on port 8089 (Event Receiving API), fail-soft, async sender; Smarteye-only eye tracking (no Tobii); recalibration hold after every 5-min break
