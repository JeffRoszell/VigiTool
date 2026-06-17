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

**Time required:** ~15 min (test mode) with shortened breaks; ~25 min with
full 5-minute breaks.

---

## 1. Launch

```bash
cd <repo> && python src/run_session.py
```

In the dialog: Participant ID `SMOKE01`, Task order `CVT → PVT`, both
difficulty orders `high → low`, **Test mode: checked** (2-minute blocks,
2 periods).

> **Note — breaks are always 5 minutes**, even in test mode. To shorten them
> for this checklist, launch via:
>
> ```bash
> python -c "import sys; sys.path.insert(0,'src'); from run_session import run; \
> run('SMOKE01',('cvt','pvt'),{'cvt':('high','low'),'pvt':('high','low')}, \
> True, break_minutes=0.5)"
> ```

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

### PVT blocks
- [ ] Fixation cross (bold +) during foreperiod; red circle replaces it
- [ ] RT feedback in ms below circle; lapses orange, valid white
- [ ] Pressing during fixation/ISI shows red **TOO EARLY**
- [ ] TASK COMPLETE results: trials, valid, anticipatory, lapses plausible
- [ ] **★ Recalibration hold also appears between tasks and between PVT blocks** (3 total per session)

### Emergency exit (run a second short session to test)
- [ ] ESC mid-block exits cleanly; partial JSON for the in-progress block exists in `data/SMOKE01/`

---

## 3. Post-run data checks

```bash
ls data/SMOKE01/
```

- [ ] 4 behavioral JSONs (`cvt_high_test_*`, `cvt_low_test_*`, `pvt_high_test_*`, `pvt_low_test_*`)
- [ ] Sidecar log `session_*.imotions.log` present; grep it:
  - [ ] `recalibration_start` / `recalibration_end` — 3 pairs
  - [ ] `cvt_hit`, `cvt_correct_rejection`, `cvt_error_omission`, `cvt_error_commission` present
  - [ ] `pvt_error_omission` (if any lapse/timeout), `pvt_error_commission` (if any anticipatory)
- [ ] If iMotions was recording: markers visible in the iMotions timeline at sensible times
- [ ] Delete `data/SMOKE01/` afterward (keep `data/` participant-free)

---

## 4. Report back

Note anything off — font sizes, stimulus visibility at seating distance,
timing feel, screen-order surprises — in KNOWN_ISSUES.md or to Jeff directly.

*Prepared June 2026 alongside the headless walkthrough; companion to
`docs/imotions_e2e_test_plan.md`.*
