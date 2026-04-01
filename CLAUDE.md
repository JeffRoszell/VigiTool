# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vigilance task suite for IRB #0007078 (PI: Poltavski, Co-PI: Gupta) at UND Psychology Department. Compares sustained attention in younger (18-35) and older (65+) adults using two tasks with concurrent EEG and eye-tracking (future integration phase).

**Lead Developer**: Jeff Roszell (BME master's student)

## Constraints

- **Pure Python 3.7+** with tkinter — no JavaScript, no web frameworks, no external runtime dependencies
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
├── REQUIREMENTS_INTEGRATION.md  # EEG/eye-tracking integration (future)
├── QUESTIONS_FOR_PI.md      # Open questions for Poltavski/Gupta
└── QUESTIONS_INTEGRATION.md # Open questions for hardware integration
```

## Tasks

### CVT (Cognitive Vigilance Task)
Based on Claypoole et al. (2019). Two-digit numbers in screen quadrants; press spacebar when digit difference is 0 or ±1. Two difficulty conditions via event rate: high (500ms ISI, ~40/min) and low (1500ms ISI, ~24/min). 24-minute blocks, 4 periods, 20 signals per block. Measures d', criterion, hit rate, FA rate, vigilance decrement.

### PVT (Psychomotor Vigilance Task)
Fixation cross → red circle; press spacebar as fast as possible. Two 24-minute sessions with high/low difficulty (500ms/1500ms ISI). Measures RT, lapses (>500ms), anticipatory responses (<100ms).

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
- **`e2e-test`** — Headless end-to-end regression test runner. Validates trial generation, metrics calculation, and JSON output schema without launching tkinter. Use after significant changes to task logic.

## Pre-Commit Hooks

Configured in `.claude/settings.json`:
1. Ruff lint check on src/ and tests/
2. Debug print() detection in src/
3. Participant data / IRB file commit blocking
4. Hardcoded path detection
5. Unit test execution

## Data Output

Participant data saves to `data/<participant_id>/` with format `<task>_<difficulty>_<YYYYMMDD_HHMMSS>.json`. See REQUIREMENTS.md for full JSON schema.

## Key Technical Notes

- Keyboard input uses only lowercase `<space>` binding (tkinter 8.5-9.0 compatibility)
- Both canvas and root bindings are set for keyboard focus capture
- SDT metrics use an approximate z-score function (no scipy dependency)
- ESC key triggers emergency exit with data save
- Task timing: ISI controls event rate (500ms = high difficulty, 1500ms = low difficulty), stimulus duration is 1000ms for CVT
