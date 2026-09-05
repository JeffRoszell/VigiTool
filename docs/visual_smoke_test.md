# Visual Smoke Test — Live Run Checklist

## Scope
Verify on real hardware what the headless walkthrough (June 2026) cannot:
actual rendering, fullscreen behavior, perceived timing, and the RA-facing
hold screens. Logic, marker content, and session flow are already covered by
`pytest tests/` and the headless walkthrough; the iMotions wire path is
covered by `docs/imotions_e2e_test_plan.md`.

Runs anywhere with PsychoPy (your Mac or the lab machine). iMotions is
**optional** — without it the client fails soft, logs a warning, and the
sidecar marker log still records everything for review.

**Time required:** ~12 min (test mode) with shortened breaks; ~20 min with
full 5-minute breaks. The PVT is a single block as of Sept 2026, so the
session is shorter and has one fewer break than earlier revisions of this
checklist.

---

## 1. Launch

```bash
cd <repo> && python src/run_session.py
```

In the dialog: Participant ID `SMOKE01`, Task order `CVT → PVT`, CVT
difficulty order `high → low`, Task display `1`, Fullscreen checked,
**Test mode: checked** (2-minute blocks, 2 periods).

There is no PVT difficulty field — the PVT has a single block with no
difficulty conditions.

> **Note — breaks are always 5 minutes**, even in test mode. To shorten them
> for this checklist, launch via:
>
> ```bash
> python -c "import sys; sys.path.insert(0,'src'); from run_session import run; \
> run('SMOKE01',('cvt','pvt'),{'cvt':{'difficulty_order':('high','low'), \
> 'skip_practice':False},'pvt':{}},True, break_minutes=0.5)"
> ```

### 1a. Extended display (do this with two monitors connected)

The reason this section exists: on the first independent lab run the task had
to be run with the second monitor unplugged, because the window captured the
cursor and iMotions could not be reached. Re-run §1 with `Task display` set to
`2` and check:

- [ ] The task goes fullscreen on **display 2**, not display 1
- [ ] The mouse moves freely on display 1 while a block is running
- [ ] iMotions is clickable on display 1 **mid-block** — start a recording and
      watch it tick over without touching the task
- [ ] Nothing of the task (window chrome, cursor, menu bar) appears on display 1
- [ ] Now select a display that does not exist (e.g. `2` with one monitor
      connected): the DISPLAY NOT FOUND warning appears and the task runs on
      display 1 rather than crashing
- [ ] Uncheck Fullscreen: the task opens in a window with the cursor visible
      *(monitoring only — windowed runs are flagged not analysable)*

---

## 2. Visual checklist (in session order)

### Startup
- [ ] Fullscreen black window, no OS chrome or cursor artifacts
- [ ] EEG BASELINE hold screen; SPACEBAR advances

### CVT practice (~5 min)
- [ ] Practice intro screen, then slow (low) → fast (high) segments
- [ ] Two-digit stimuli appear in all 5 locations (4 quadrants + center) with slight jitter
- [ ] Practice feedback shows **HIT** (green), **FALSE ALARM** (red), **MISS** (red), correct rejections white — large font, readable
- [ ] Practice does **not** crash with iMotions enabled *(regression: period KeyError fixed June 2026)*

### CVT blocks
- [ ] Block 1 instructions state difficulty HIGH / 500 ms
- [ ] Stimulus on ~1 s; blank/fixation ISI feels distinct between high (500 ms) and low (1500 ms) blocks
- [ ] In-block feedback only on responses (HIT / FALSE ALARM), small font at bottom
- [ ] BLOCK COMPLETE results screen: hits, false alarms, d′, mean RT plausible
- [ ] Break countdown (MM:SS) ticks down smoothly
- [ ] **★ EYE-TRACKING RECALIBRATION hold appears after the break** — text legible, waits indefinitely, SPACEBAR continues

### PVT block (single, 10 min — 2 min in test mode)
- [ ] Instructions state the duration and mention **no** difficulty condition
- [ ] Fixation cross (bold +) during the interval; red circle replaces it
- [ ] **★ The red circle is ROUND, not an ellipse** — check on a widescreen
      monitor, where the old `norm`-units bug was most visible. Its diameter
      should be about a tenth of the screen height
- [ ] Gaps between trials feel like whole-second steps (1–10 s), not a smooth
      continuum
- [ ] RT feedback in ms below circle for about half a second; lapses orange,
      valid white
- [ ] Pressing before the circle shows red **TOO EARLY**
- [ ] TASK COMPLETE results: trials, valid, anticipatory, lapses plausible
- [ ] Session ends after the single PVT block — there is **no** second PVT
      block and no break inside the PVT
- [ ] **★ Recalibration hold appears between the CVT blocks and between
      tasks** (2 total per session, down from 3)

### Emergency exit (run a second short session to test)
- [ ] ESC mid-block exits cleanly; partial JSON for the in-progress block exists in `data/SMOKE01/`

---

## 3. Post-run data checks

```bash
ls data/SMOKE01/
```

- [ ] 3 behavioral JSONs (`cvt_high_test_*`, `cvt_low_test_*`, `pvt_test_*`)
      — the PVT filename carries no difficulty
- [ ] The PVT JSON has `metadata.schema_version: 2`, no `difficulty` and no
      `isi_ms`, and `metadata.display` matching the monitor you chose
- [ ] Every `trial_data.foreperiod_ms` is a whole multiple of 1000
- [ ] Sidecar log `session_*.imotions.log` present; grep it:
  - [ ] `recalibration_start` / `recalibration_end` — 2 pairs
  - [ ] `pvt_block` scene pair — and **no** `pvt_high_block` / `pvt_low_block`
  - [ ] `cvt_hit`, `cvt_correct_rejection`, `cvt_error_omission`, `cvt_error_commission` present
  - [ ] `pvt_error_omission` (if any lapse/timeout), `pvt_error_commission` (if any anticipatory)
- [ ] If iMotions was recording: markers visible in the iMotions timeline at sensible times
- [ ] Delete `data/SMOKE01/` afterward (keep `data/` participant-free)

---

## 4. Report back

Note anything off — font sizes, stimulus visibility at seating distance,
timing feel, screen-order surprises — in KNOWN_ISSUES.md or to Jeff directly.

*Prepared June 2026 alongside the headless walkthrough; companion to
`docs/imotions_e2e_test_plan.md`. Updated Sept 2026 for the single-block PVT
and extended-display support.*
