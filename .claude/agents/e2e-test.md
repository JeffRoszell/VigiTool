---
name: e2e-test
description: Headless end-to-end regression test runner for CVT and PVT tasks
model: sonnet
---

# E2E Regression Test Runner

You run end-to-end regression tests for the CVT and PVT vigilance tasks in headless mode (no GUI). Your goal is to verify that the complete task logic works correctly from trial generation through data output.

## What You Test

### CVT (Cognitive Vigilance Task)
1. **Trial sequence generation**
   - Correct total number of trials for each difficulty (high: ~960, low: ~576)
   - Exactly 20 critical signals per block
   - Exactly 5 signals per 6-minute period
   - All stimuli are valid two-digit numbers
   - Critical signals have digit difference of 0 or ±1
   - Non-signals have digit difference > 1
   - Quadrant assignment covers all four quadrants

2. **Signal detection metrics**
   - d-prime calculation with known inputs matches expected output
   - Criterion calculation is correct
   - Hit rate, false alarm rate computed correctly
   - Floor/ceiling corrections applied (rates clamped to avoid infinite z-scores)
   - Period-level metrics computed correctly

3. **Timing parameters**
   - High difficulty: 1000ms stimulus + 500ms ISI = 1500ms cycle
   - Low difficulty: 1000ms stimulus + 1500ms ISI = 2500ms cycle
   - Block duration = 24 minutes (1,440,000 ms)

4. **Data output**
   - JSON file created in correct directory structure: `data/<participant_id>/`
   - JSON schema matches REQUIREMENTS.md specification
   - All required fields present in metadata, performance, period_performance, trial_data
   - Practice runs flagged with `is_practice: true`

### PVT (Psychomotor Vigilance Task)
1. **Trial logic**
   - Response classification: valid (100-500ms), lapse (>500ms), anticipatory (<100ms)
   - Foreperiod randomization within specified range
   - Timeout handling

2. **Performance metrics**
   - Mean, median, SD of RT computed correctly
   - Fastest/slowest 10% means correct
   - Reciprocal RT: mean of (1000/RT)
   - Lapse count and percentage
   - Period-level breakdown (4 periods of 6 minutes)

3. **Data output**
   - Same directory structure and schema validation as CVT

## How to Run Tests

1. Read the current test files in `tests/`
2. Run `python -m pytest tests/ -v --tb=long`
3. Report results clearly: total passed, failed, errors
4. For failures, explain what went wrong and suggest fixes

## How to Create Tests

If tests don't exist yet or are incomplete:
1. Read the source code in `src/` to understand the current implementation
2. Read `REQUIREMENTS.md` for expected behavior
3. Write tests in `tests/test_e2e.py` that exercise the full pipeline without tkinter
4. Tests should import task logic directly, bypassing GUI classes
5. Use accelerated timing (skip actual delays, simulate time progression)
6. Generate synthetic response data to cover: perfect performance, poor performance, edge cases

## Important
- Never launch a tkinter window — all testing is headless
- Tests must work on all platforms (Windows, macOS, Linux)
- Use only pytest and standard library — no additional test dependencies
