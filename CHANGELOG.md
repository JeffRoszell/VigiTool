# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to the versioning scheme described in
[VERSIONING.md](VERSIONING.md).

Each release entry records the **PI protocol revision** the code targets.

## [Unreleased]

Incorporates PI answers to the workflow & study-design questions
(`Jeff_questions_U2`, June 2026).

### Added
- **Per-trial outcome markers (CVT).** Every scored trial emits a discrete
  iMotions marker: `cvt_hit`, `cvt_correct_rejection`, `cvt_error_omission`
  (miss), or `cvt_error_commission` (false alarm).
- **Error markers (PVT).** Lapses and timeouts emit `pvt_error_omission`;
  anticipatory presses (pre- and post-stimulus) emit `pvt_error_commission`.
- **Recalibration holds.** After every 5-minute break (between blocks within
  a task and between CVT and PVT), the app holds on an RA screen until
  eye-tracking recalibration is confirmed, bracketed by
  `recalibration_start`/`recalibration_end` markers
  (`session_utils.recalibration_hold`).

### Changed
- Docs updated with PI decisions: Smarteye-only eye tracking (no Tobii
  integration), sub-millisecond sync target met by localhost TCP (no hardware
  trigger), RA starts the iMotions recording (Remote Control flag stays off),
  one shared iMotions study with a respondent per participant.
- **Lab software versions pinned (resolves Q10).** iMotions **11.1.5** and
  B-Alert Live **3.1x** confirmed (U. Gupta). Marker/Remote Control wire format
  is unchanged across the iMotions 11.1.x line, so no `src/` change is required;
  `REQUIREMENTS_INTEGRATION.md` and `QUESTIONS_INTEGRATION.md` updated, and
  `docs/imotions_e2e_test_plan.md` gains a §0a version-compatibility checklist
  (B-Alert Live 3.1x recognition, Smart Eye Tracker software ≥ 10.1.2 for the
  every-break recalibration path, live marker-byte diff). See
  `INTEGRATION_VERSION_PLAN.md`.

## [0.2.0] – 2026-05-06 — Protocol: U3

Aligns the CVT and PVT implementations with the *Cognitive Vigilance Task
U3* design document (PI: Poltavski). Substantial protocol changes: schema
break is intentional and allowed under the pre-1.0 versioning rule.

### Added
- **CVT central display location.** Stimuli now appear in 5 locations
  (4 quadrants + center) randomized per trial.
- **Per-period spatial distribution.** Each 6-minute period contains
  exactly 5 critical signals — one in every location — to enforce
  central + peripheral attentional sampling.
- **Fixation cross during ISI.** A `+` is shown at screen center
  throughout the inter-stimulus blank.
- **Single CVT practice session.** 2.5 min low + 2.5 min high at the
  start of the experiment, preceded by an intro screen with three
  example critical signals. Live trials show large-font feedback for
  every outcome (HIT, FALSE ALARM, MISS, CORRECT). Practice data is
  not saved.
- **Timed 5-minute breaks** between difficulty blocks within a task and
  between tasks (when launched via `run_session.py`). On-screen
  countdown; ESC aborts.
- **Session orchestrator (`src/run_session.py`).** Top-level launcher
  that prompts for participant ID, task order (CVT→PVT or PVT→CVT),
  per-task difficulty order, then runs both tasks back-to-back with
  the between-task break. Begins with an EEG-baseline hold screen.
- **Shared session helpers (`src/session_utils.py`)** — `timed_break`,
  `message_screen`, `BREAK_MINUTES`.
- **Versioning docs** — `VERSIONING.md` and this `CHANGELOG.md`.

### Changed
- **JSON schema (breaking):**
  - `metadata.age` removed from CVT and PVT output. Age is collected on
    a paper questionnaire per U3 protocol; no demographic data is
    written to disk.
  - `trial_data[*].quadrant` renamed to `trial_data[*].location`. Valid
    values: `upper_left`, `upper_right`, `lower_left`, `lower_right`,
    `center`. Field renamed to remain semantically accurate as more
    locations may be added in future revisions.
- **Launch dialog (both tasks):**
  - Removed Age field.
  - "Difficulty" replaced with "Difficulty order" (`high → low` or
    `low → high`) — both blocks now run in one session.
- `SIGNALS_PER_PERIOD` is a constant (5), no longer a per-mode dict.
- `REQUIREMENTS.md` updated for all schema and flow changes.

### Notes for reviewers
- Counterbalancing is RA-managed externally; the application records
  the chosen order but does not enforce a counterbalancing scheme.
- EEG markers / TCP triggers remain Phase 2 work.
- Headless tests pass (29/29). Manual PsychoPy verification still
  needed for: fixation rendering during ISI, practice intro layout,
  large-font feedback, timed-break countdown UI.

## [0.1.0] – 2026-04-22 — Protocol: pre-U3 (Phase 1 baseline)

Initial PsychoPy implementation of CVT and PVT.

### Added
- CVT task with 4-quadrant stimulus presentation, SDT metrics
  (d′, criterion), per-period vigilance-decrement breakdown.
- PVT task with fixation → red circle, RT classification (valid /
  lapse / anticipatory / timeout), reciprocal-RT and 10%-tail metrics.
- Headless pytest suite covering trial generation and metrics.
- Custom Claude Code agents: `sme`, `compliance`, `e2e-test`.
- Pre-commit hooks: ruff, debug-print detection, IRB-data block,
  hardcoded-path detection, unit tests.
- CI workflow.
- Migration from legacy tkinter implementation to PsychoPy.
