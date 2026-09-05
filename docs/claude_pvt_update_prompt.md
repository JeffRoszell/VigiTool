# Prompt for Claude: Psychomotor Vigilance Task (PVT) Updates

## Background (Context for Claude)

We need to update our `pvt_task.py` implementation in the UND Psychology Department
vigilance task suite. Following the first independent lab run (U. Gupta and James
running the task without the developer present, Lina observing, August 2026), the
Co-PI requested changes to the PVT block structure and stimulus, and reported a
blocking usability problem when running the task on a machine with an extended
display.

The codebase is located in `src/pvt_task.py`, with session orchestration in
`src/run_session.py`. Please make sure that your changes adhere to our existing
standards (see `CLAUDE.md`), specifically keeping it in pure Python using PsychoPy,
and maintaining our `data/` logging schema without violating IRB constraints.

### Reference specification

The Co-PI has designated the Millisecond Inquisit **Perceptual Vigilance Task
(keyboard)** technical manual as the authoritative specification for the PVT:

<https://www.millisecond.com/library/v7/perceptualvigilancetask/perceptualvigilancetask_keyboard/perceptualvigilancetask_keyboard/perceptualvigilancetask_keyboard.manual>

**Tie-breaker rule (developer decision, Sept 2026):** where our current
implementation and the manual disagree, or where a parameter is ambiguous, follow
the manual. Where the manual is *silent*, keep the existing implemented value and
flag it — silence is not a conflict.

Note that high/low difficulty remains a **CVT-only** factor. It is being removed
from the PVT entirely. Do not touch the CVT difficulty logic.

---

## Required Modifications

### 1. Block Structure (PVT)

*   **Duration:** A single **10-minute** block. The manual specifies "recommended
    minimum time is 600000ms => 10 min". This replaces the current two 24-minute
    blocks.
*   **Difficulty conditions:** **Remove entirely.** There is no high/low PVT
    condition. `ISI_S = {"high": 0.5, "low": 1.5}` and every code path that
    branches on PVT difficulty must go.
*   **No post-response ISI.** The manual has no separate inter-stimulus interval.
    The random interval *is* the entire gap between trials. Delete the ISI concept
    rather than replacing it with a fixed value.
*   **Session flow:** `run_full_session()` no longer loops over a difficulty pair.
    One block means there is no longer a between-block break inside the PVT, and
    therefore one fewer recalibration hold. The 5-minute break *between tasks* in
    `run_session.py` is unaffected.

### 2. Trial Intervals (PVT)

*   The interval preceding each stimulus is drawn **randomly with replacement from
    the discrete set** {1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000,
    10000} ms.
*   This is a real change: the current `FOREPERIOD_RANGE` uses
    `random.uniform(1.0, 10.0)`, a continuous draw. The manual specifies discrete
    1-second steps.
*   Extract this into a pure, importable sampling function (see TDD section) so it
    can be tested without a display.

### 3. Stimulus Geometry (PVT) — bug fix

*   **The circle currently renders as an ellipse.** Root cause: the `visual.Window`
    is created with `units="norm"` (in both `pvt_task.main()` and
    `run_session.run()`), where one horizontal unit and one vertical unit are not
    equal on a widescreen display. `visual.Circle(win, radius=0.08)` therefore
    inherits the window units and is stretched horizontally.
*   **Fix on the stimulus, not the window.** Set `units="height"` on the `Circle`
    only. Changing the window units would silently re-layout every other stimulus
    in both the CVT and the PVT.
*   **Size:** the manual's default is a diameter of "10% of the vertical screen",
    i.e. `radius=0.05` in height units.
*   **Colour:** red (manual default) — unchanged.
*   **Position:** fixed screen centre (manual default) — unchanged. Do not
    implement the manual's optional random 9-position mode.

### 4. Feedback (PVT)

*   **RT feedback duration: 0.5 s.** The manual specifies `rtFeedbackDuration:
    500ms`. Our current `FEEDBACK_DURATION = 1.0` came from a June 2026 PI
    decision made before the manual was designated as the reference; under the
    tie-breaker rule the manual wins. Flag this in the change summary so the PI can
    override it at the next weekly meeting if the 1 s value was deliberate.

### 5. Parameters the Manual Does Not Specify — keep as-is

Do not change these. They are listed so the reviewer can see they were considered:

*   **Lapse threshold:** 500 ms (`LAPSE_THRESHOLD_MS`) — retained, standard PVT.
*   **Anticipatory threshold:** 100 ms (`VALID_RT_MIN_MS`) — retained.
*   **Stimulus timeout:** 30 s (`STIM_TIMEOUT`) — retained, per June 2026 PI
    decision.
*   **Fixation cross during the interval** — retained.

### 6. Open Question — Period Structure (do not guess)

`NUM_PERIODS["full"] = 4` was designed as 4 x 6 min across a 24-minute block. Over
10 minutes that becomes either **4 x 2.5 min** or **2 x 5 min**. The manual defines
no period structure at all, so the tie-breaker rule does not apply.

**Implement 4 periods (4 x 2.5 min) as the provisional default**, for consistency
with the CVT's four-period vigilance decrement analysis, and raise it as an
explicit agenda item at the first weekly meeting. It affects
`compute_period_metrics()` and the decrement analysis, not task presentation, so it
is cheap to change later.

### 7. Extended-Display Support (both tasks) — lab blocker

During the independent run the task had to be executed with the second monitor
physically disconnected, because the cursor could not be controlled once the
fullscreen window was up. As a result iMotions recording was started and then ran
unmonitored in the background for the whole session. This is the highest-priority
usability fix.

*   **Add explicit display selection.** `visual.Window` is currently created with
    `fullscr=True` and no `screen=` argument, so it always claims display 0. Add a
    **"Task display"** integer field (default `0`) to the launch dialogs in
    `run_session.main()`, `pvt_task.main()` and `cvt_task.main()`, and thread it
    through to every `visual.Window(...)` call as `screen=`.
*   **Goal state:** the task runs fullscreen on the participant monitor while the
    RA retains a usable cursor on the operator monitor to monitor the iMotions
    recording live.
*   Keep `allowGUI=False` for the participant window.
*   Add a short pre-flight note to the RA runbook: confirm which display index is
    the participant screen before the participant is seated.

### 8. Documentation & Marker Consistency

*   **iMotions marker labels change.** `PvtMarkerEmitter.block_start()` /
    `block_end()` currently emit `pvt_<difficulty>_block`. With difficulty gone this
    must become a single stable label (`pvt_block`). **Flag this prominently in the
    change summary** — the Co-PI selects epochs in iMotions by marker name, so this
    is a coordination item, not just a rename.
*   **Data schema.** `save_data()` writes `pvt_<difficulty><suffix>_<ts>.json` and a
    `metadata` block containing `difficulty` and `isi_ms`. Both fields become
    meaningless. Update the filename pattern and the schema, and update the schema
    documented in `REQUIREMENTS.md`.
*   **Update the PVT description in all four places it has drifted:**
    `README.md:17`, `CLAUDE.md:41`, `REQUIREMENTS.md:59`, `REQUIREMENTS.md:122`.
*   **Add a `CHANGELOG.md` `[Unreleased]` entry** recording the protocol change and
    the intentional schema break, per `VERSIONING.md`.

---

## Development Approach — Test-Driven (required)

Work test-first. Do not write implementation code before the failing test exists.

The existing suite runs **without PsychoPy** (`pytest tests/ -v` in CI), and that
must stay true. This constrains the design in a useful way: every manual-derived
parameter should live in a named module-level constant or a pure function, so the
specification is asserted directly rather than inferred from rendering behaviour.

**Cycle, per change:**

1.  Write the failing test in `tests/` first. Run it. Confirm it fails *for the
    right reason*.
2.  Write the minimum implementation to pass it.
3.  Run `pytest tests/ -v` and `ruff check src/ tests/`.
4.  Refactor with the suite green.

**Required test coverage — write these before touching `src/`:**

*   `sample_interval()` returns only values from the discrete 1000–10000 ms set;
    over many draws it produces more than one distinct value (i.e. it is actually
    random) and never a non-multiple of 1000 ms.
*   Block duration constant equals 600 s / 10 min.
*   The stimulus spec constants: radius `0.05`, units `"height"`, colour red. This
    is what pins the ellipse fix in a headless test — assert the constants the
    `Circle` is constructed from, since the geometry itself cannot be tested
    without a window.
*   `FEEDBACK_DURATION == 0.5`.
*   Marker emitter produces `pvt_block` with no difficulty in the label. **Update
    the existing assertion at `tests/test_pvt_metrics.py:177`**, which currently
    expects `pvt_low_block`.
*   `save_data()` output contains no `difficulty` or `isi_ms` key, and the filename
    matches the new pattern.
*   `compute_period_metrics()` over the chosen period count.
*   Regression: no symbol in `src/` still references `ISI_S` or a PVT difficulty
    argument.

**Not unit-testable — verify manually and record in the change summary:** the
rendered circle's aspect ratio, and extended-display behaviour. Add both to
`docs/visual_smoke_test.md` as explicit manual checks, including a two-monitor
case that confirms the RA cursor stays free on the operator display.

---

## Your Task

1.  **Analyze current implementation.** Review `src/pvt_task.py` and
    `src/run_session.py` to map every code path that branches on PVT difficulty,
    every consumer of `ISI_S`, and every `visual.Window(...)` construction site.
2.  **Write the failing tests** listed above, and confirm they fail correctly.
3.  **Implement** the changes in sections 1–8.
4.  **Validate output.** Confirm the saved JSON still parses cleanly and that the
    schema change is deliberate, documented in `REQUIREMENTS.md`, and recorded in
    `CHANGELOG.md`. Run the `e2e-test` agent for a headless regression pass.
5.  **Produce a change summary** for the weekly meeting that separately lists:
    (a) manual-derived changes applied under the tie-breaker rule, (b) the two
    items needing Co-PI sign-off — the marker label change and the RT feedback
    duration — and (c) the open period-structure question from section 6.

---

*Prepared by Jeff Roszell — September 2026*
*Source: U. Gupta correspondence, August 2026, following the first independent lab run*
