# Integration Version Update — Plan

## Vigilance Task Suite — iMotions 11.1.5 / B-Alert Live 3.1x

**IRB #0007078 · PI Poltavski · Co-PI Gupta · Lead dev Jeff Roszell**
**Prepared June 2026 · Status: proposal for review (no code changed yet)**

---

## 1. Why this document exists

The lab's biosensor software versions were the last open item in the integration
spec (`QUESTIONS_INTEGRATION.md` Q10). Utkarsh has now confirmed them:

- **iMotions: 11.1.5** (current install)
- **B-Alert Live: 3.1x** — in progress; the renewed ABM license is being
  activated, after which iMotions will run the current B-Alert Live build.

This plan records what those versions mean for our code, what we should change
and why, and how the change reaches the current branch and then `main`.

---

## 2. Bottom line

**No forced changes to `src/`.** The marker wire protocol our code implements is
stable across the entire iMotions 11.1.x line, and our task software never talks
to B-Alert directly — everything routes through iMotions. The work is therefore
(a) pinning the confirmed versions into the integration docs, (b) hardening the
lab end-to-end checklist with version-specific verification steps, and
(c) two lab-side compatibility confirmations that are not code at all.

The reason to still do this carefully: our code was validated against the
**iMotions Feb 2026 reference implementation (= 11.1.0)**, and the lab is on
**11.1.5**. Nothing in the published 11.1.1–11.1.3 release notes touches the
Event Receiving or Remote Control API, but 11.1.4/11.1.5 notes are newer than the
public snapshot and have not yet been read, and the actual wire bytes have never
been exercised against a live install. That gap is closed by verification, not
by speculative code changes.

---

## 3. Findings from the integration documentation

### 3.1 iMotions API is stable across 11.1.x

- iMotions exposes the same two TCP APIs we already target: **Event Receiving
  (port 8089)** for markers and **Remote Control (port 8087)** for study control.
  Architecture is unchanged — iMotions is the server, our script is the client.
- The published release notes for **11.1.1, 11.1.2, 11.1.3** contain no changes
  to the Event Receiving or Remote Control API, the marker format, or the ports.
  The 11.1.x work was eye-tracking, replay, motion-capture, and survey fixes.
- Our marker shapes (`M;2;;;<name>;<desc>;D|N|E;…\r\n`) and Remote Control shapes
  (`R;1;;<CMD>;…\r\n`) therefore remain the documented format. The `2` and `1`
  are the API *protocol* version fields, not the iMotions application version —
  they do not change when the app goes 11.1.0 → 11.1.5.

### 3.2 Two iMotions 11.x changes worth noting (neither breaks us)

- **Marker export is now clear text** (previously URL-encoded). We send plain
  labels with no reserved characters, so offline parsing of exported markers is
  unaffected — but the E2E check should eyeball one exported marker to confirm.
- **Event API now offers JSON serialization and EventAPI-over-LSL** as options.
  We use neither; the plain TCP semicolon format stands. Listed here only so we
  don't accidentally "upgrade" into an unnecessary format change.

### 3.3 Smart Eye (eye tracking) — a real dependency

- iMotions **11.1.0 fixed a bug where Smart Eye trackers fail to calibrate if the
  Smart Eye Tracker *software* is version 10.0.0 or earlier**; iMotions supports
  Smart Eye Tracker software 10.1.2+.
- Our protocol mandates **eye-tracking recalibration after every 5-minute break**
  (`session_utils.recalibration_hold`, `recalibration_start/end` markers). If the
  lab's Smart Eye software is old, those mid-session recalibrations can fail even
  though iMotions 11.1.5 itself is fine. **Confirm Smart Eye Tracker software
  ≥ 10.1.2 on the lab machine.** This is a config check, not a code change.

### 3.4 B-Alert Live 3.1x — no code, but a compatibility gate

- The task software does **not** communicate with B-Alert (confirmed, Q1). EEG is
  acquired by iMotions through its bundled ABM B-Alert SDK; we only send markers
  to iMotions, which timestamps and aligns the EEG stream.
- B-Alert Live is the ABM acquisition software/SDK iMotions drives. iMotions
  periodically bumps the ABM SDK it ships, and has historically shipped fixes
  tied to the X24 (e.g. a channel-label correction for X24 PSD export, and an
  impedance-check disconnect fix). **Confirm with iMotions/ABM support that
  iMotions 11.1.5 recognizes the renewed B-Alert Live 3.1x install** once the
  license activates. Because our EEG indices (Engagement Index at Cz/P3/P4/Pz,
  Frontal Theta, etc.) depend on correct channel labelling, this confirmation is
  worth doing explicitly during E2E rather than assuming.

---

## 4. What we will change, and why

| # | Change | Files | Why |
|---|--------|-------|-----|
| A | Pin confirmed versions | `REQUIREMENTS_INTEGRATION.md` §5.3/§7, `QUESTIONS_INTEGRATION.md` Q10 | Closes the last open question; makes "validated against" precise (11.1.5, not "Feb 2026") |
| B | Harden the lab E2E checklist | `docs/imotions_e2e_test_plan.md` | Turn the version info into concrete pre-flight verification before participants run |
| C | Record lab-side facts | same docs | B-Alert Live 3.1x + Smart Eye software version belong in the spec, not just an email |
| D | (Conditional) wire-format fix | `src/imotions_api.py` `format_*` helpers only | Only if E2E shows a byte-level mismatch on 11.1.5; the format is already isolated so the change stays surgical |

**New E2E verification steps (Change B), added to the existing checklist:**

1. Record the exact iMotions build (confirm **11.1.5**) and **read the 11.1.4 /
   11.1.5 release notes** for any late API change (not in the public snapshot yet).
2. Confirm **B-Alert Live 3.1x** is installed, licensed, and listed as a connected
   EEG device inside iMotions; run an impedance check and one-minute capture.
3. Confirm **Smart Eye Tracker software ≥ 10.1.2**, then exercise a *mid-session
   recalibration* (not just the initial calibration) to validate the
   every-break recalibration path against this version.
4. Run the existing Event Receiving smoke test and **diff the actual marker bytes
   against `format_discrete` / `format_scene_start` / `format_scene_end`** on the
   live 11.1.5 install; export one marker and confirm it lands as clear text.
5. (Only if `IMOTIONS_REMOTE_ENABLED` is ever turned on) verify the
   `R;1;;<CMD>;…` Remote Control bytes against the 11.1.5 reference — still the
   dormant `TODO(lab E2E)` in `imotions_api.py`.

**What we are deliberately *not* changing:** the marker emitters, ports, async
fail-soft sender, config flags, or session orchestration. They are already
correct for the documented 11.1.x protocol; touching them adds risk for no
benefit until E2E proves a mismatch.

---

## 5. Getting this to the current branch, then to main

### 5.1 Where things stand

- Current branch **`feature/pi-answers-u2`** is **15 commits ahead of and 0 behind
  `origin/main`** — the whole iMotions integration lives here and has **not yet
  merged to main**. `feature/imotions-integration` is already folded in.
- So this version update is the natural *final* piece of the integration branch:
  it resolves Q10, the last open item that branch was built to close.

### 5.2 Recommended path

1. **Commit on the current branch.** Make changes A–C as one or two small commits
   directly on `feature/pi-answers-u2` (e.g. `docs: pin iMotions 11.1.5 /
   B-Alert Live 3.1x; harden E2E checklist`). Keeping them on the integration
   branch keeps the eventual PR self-contained rather than spawning a second PR.
   *(Alternative if you prefer isolation: cut `chore/imotions-11.1.5-version-pin`
   off the current branch and merge it back before the main PR.)*
2. **Update the changelog.** Add the version-pin + E2E hardening under the
   existing `## [Unreleased]` block in `CHANGELOG.md`, tagged with the PI
   protocol revision. Per `VERSIONING.md` this rides along in the integration
   **MINOR** release (new EEG/eye-tracking integration); no separate bump.
3. **Green the gates locally:** `ruff check src/ tests/` and `pytest tests/`.
   Changes A–C are docs only, so the suite stays green; this just satisfies the
   pre-commit hooks (ruff, debug-print, data-leak, hardcoded-path, unit tests).
4. **Run the project agents** before the PR: `compliance` (PII / participant-data
   / `.gitignore`) and `e2e-test` (headless trial-gen, metrics, JSON schema).
5. **Open the PR `feature/pi-answers-u2` → `main`.** This is the integration PR;
   the version pin makes it reviewable as "integration complete, pending live
   hardware sign-off."
6. **Set the version + tag on merge.** Bump `pyproject.toml` to the integration
   MINOR, squash-or-merge per repo norm, and create the annotated `vX.Y.Z` tag on
   the merge commit (VERSIONING.md tagging workflow).

### 5.3 The one gate that is *not* code

Live **E2E sign-off on the lab machine** (Section 4 steps 1–5) needs the B347D
hardware, the renewed B-Alert Live license active, and the joint iMotions
study-setup call with the PI. The code/docs PR can land on `main` first, with
lab E2E tracked as the single remaining open item — exactly how
`REQUIREMENTS_INTEGRATION.md §7` already frames it. Do **not** run participants
until that sign-off is recorded.

---

## 6. Open items after this lands

- Read iMotions **11.1.4 / 11.1.5** release notes directly (newer than the public
  page snapshot used here) and confirm no late API change.
- Confirm **iMotions 11.1.5 ↔ B-Alert Live 3.1x** compatibility with ABM/iMotions
  support once the license activates.
- Confirm **Smart Eye Tracker software ≥ 10.1.2** and validate mid-session
  recalibration.
- Build the shared `Vigilance_CVT_PVT` iMotions study with the PI (post-handover
  from James).

---

### Sources

- [iMotions Lab — Release Notes (11.1.0–11.1.3)](https://imotions.com/products/imotions-lab/release-notes/)
- [iMotions Lab — API (Event Forwarding / Event Receiving / Remote Control)](https://imotions.com/products/imotions-lab/developers/api/)
- [iMotions — B-Alert X24 hardware / EEG module](https://imotions.com/products/hardware/b-alert-x24/)
- Repo: `REQUIREMENTS_INTEGRATION.md`, `QUESTIONS_INTEGRATION.md`, `docs/imotions_e2e_test_plan.md`, `src/imotions_api.py`
