# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to the versioning scheme described in
[VERSIONING.md](VERSIONING.md).

Each release entry records the **PI protocol revision** the code targets.

## [Unreleased]

Two tranches: the June 2026 PI answers to the workflow & study-design
questions (`Jeff_questions_U2`), and the September 2026 PVT protocol change
requested by the Co-PI after the first independent lab run.

### PVT protocol change — Sept 2026 (Protocol: Inquisit manual)

The Millisecond Inquisit Perceptual Vigilance Task (keyboard) manual is now
the authoritative PVT specification. Tie-breaker rule: where the code and the
manual disagree, or a parameter is ambiguous, the manual wins; where the
manual is silent, the implemented value stands.

#### Changed
- **PVT is a single 10-minute block** (was two 24-minute blocks).
- **PVT high/low difficulty removed.** Difficulty remains a CVT-only factor.
- **Trial intervals** are drawn with replacement from the discrete
  {1000…10000} ms set, replacing a continuous `random.uniform(1, 10)`.
- **RT feedback 1.0 s → 0.5 s**, overriding a June 2026 decision under the
  tie-breaker rule. Flagged in REQUIREMENTS §7 for confirmation.
- **Periods** stay at four, now 2.5 minutes each. `period_seconds()` divides
  as float — 10/4 is the first non-integer period length in this suite.
- `run_full_session` arguments after `participant_id` are keyword-only, so a
  stale positional call raises instead of sliding `test_mode` into the slot
  `difficulty_order` used to occupy.
- Session recalibration holds drop from three to two: the PVT no longer has
  an internal break.
- `run_session` builds per-task keyword options (`build_task_options`) rather
  than passing a uniform argument list to both tasks.

#### Fixed
- **The PVT target rendered as an ellipse.** It inherited the window's `norm`
  units, which are anisotropic on a widescreen. The stimulus now specifies
  `height` units explicitly, at the manual's 10%-of-vertical-screen diameter.
- **The task always claimed display 0**, capturing the cursor there. On the
  lab machine this forced the RA to disconnect the second monitor and left an
  iMotions recording unmonitored for a whole session.

#### Added
- **Display selection.** Launch dialogs gain a 1-based `Task display`
  dropdown and a `Fullscreen` checkbox; `session_utils.make_window` is the
  single window construction point for all three entry points. An
  out-of-range choice warns and falls back to display 1.
- 33 headless tests covering the spec constants, the discrete interval draw,
  the circle geometry, schema v2, the keyword-only signatures, display
  selection, and a guard pinning `cvt_task`'s identically-named constants.

#### Removed
- **BREAKING** — iMotions markers `pvt_high_block` and `pvt_low_block`,
  replaced by a single `pvt_block`. Saved iMotions epoch definitions keyed on
  the old labels will match nothing and yield *empty epochs* rather than an
  error. Coordinate with Dr. Gupta before the next run.
- **BREAKING** — PVT schema v2 drops `difficulty`, `isi_ms` and
  `foreperiod_range_ms` from metadata, and the difficulty segment from the
  filename (`pvt_<ts>.json`). Adds `schema_version`, `spec_source`, the full
  parameter set and `display`. An absent `schema_version` means v1, which is
  a **different protocol** and must not be pooled with v2 data.
- `ISI_S` and `FOREPERIOD_RANGE` deleted rather than left unused, so a future
  change cannot quietly reinstate the double-counted gap.

#### Notes
- KNOWN_ISSUES rows 5–7 are retracted: the legacy PVT's 10-minute,
  no-difficulty, 1–10 s behaviour was correct. The implementation converges
  on it by way of the manual; `legacy/` stays frozen.
- A 10-minute block yields roughly 95 trials, so period-level lapse counts
  are low-powered and descriptive. Accepted consequence of the manual.
- **IRB:** the shorter PVT changes the stated participant time commitment
  under IRB #0007078. Confirm with the PI whether a protocol modification
  must be filed before the next run.

### June 2026 tranche

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
