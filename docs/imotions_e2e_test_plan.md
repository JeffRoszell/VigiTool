# iMotions Integration — Manual End-to-End Test Plan

## Scope
Validate the iMotions integration on the actual lab machine (Research Room B347D)
before running participants. The unit + integration test suite (`pytest tests/`)
covers everything that can be tested without iMotions present; this document
covers what cannot.

**Required:** lab machine with iMotions installed, a defined iMotions study
(name matching `IMOTIONS_STUDY_NAME`, default `Vigilance_CVT_PVT`), B-Alert
X-24 and Smarteye paired through iMotions (PI June 2026: no Tobii).

**Roles:** Tester (Jeff or RA). No participant data — use a pilot ID such as
`PILOT01`.

---

## 0. Prerequisites

- [ ] Repository on the lab machine, branch `feature/imotions-integration`
- [ ] `pip install -e ".[dev]"` succeeds
- [ ] `pytest tests/` runs green
- [ ] iMotions Global Settings → API → Event Receiving API enabled, TCP, port 8089
- [ ] iMotions Global Settings → API → Remote Control API enabled, TCP, port 8087
- [ ] Note the installed iMotions version (resolves `QUESTIONS_INTEGRATION.md` Q10)

---

## 1. Smoke test — Event Receiving API connect

**Setup**
- [ ] Open iMotions, load the study, begin a recording with a throwaway respondent.
- [ ] Open a Python REPL on the lab machine.

**Steps**
```python
from imotions_api import EventReceivingAPI
c = EventReceivingAPI()
assert c.connect() is True
c.discrete("e2e_smoke", "hello from python")
c.scene_start("e2e_smoke_block")
c.scene_end("e2e_smoke_block")
c.close()
```

**Pass criteria**
- [ ] `connect()` returns True (no `ConnectionRefusedError`)
- [ ] Three markers appear in the iMotions timeline (one discrete, one scene
      pair) with correct names
- [ ] No errors in the iMotions log
      (`C:\ProgramData\iMotions\Lab_XG\Log\imotions.log`)

**If connect fails**
- iMotions not in "recording" state? Markers go to the active recording.
- API not enabled in iMotions Global Settings?
- Port collision? Check `netstat -an | findstr 8089`.

---

## 2. Smoke test — Remote Control API connect *(if enabling Q12 path)*

**Setup**
- [ ] iMotions open, study loaded, no recording started.
- [ ] Set env var: `set IMOTIONS_REMOTE_ENABLED=1`

**Steps**
```python
from imotions_api import RemoteControlAPI, format_run_study, format_cancel_study
r = RemoteControlAPI()
assert r.connect() is True
print("RUN bytes:", format_run_study("Vigilance_CVT_PVT", "PILOT01"))
r.start_study("Vigilance_CVT_PVT", "PILOT01")
# wait ~3 seconds, watch iMotions UI for recording start
r.stop_study()
r.close()
```

**Pass criteria**
- [ ] `connect()` returns True
- [ ] iMotions begins recording within a few seconds of `start_study`
- [ ] iMotions shows respondent name "PILOT01"
- [ ] `stop_study` ends the recording cleanly

**If `start_study` succeeds at the socket level but iMotions doesn't react**
- The wire format may differ from what `format_run_study` emits. Compare
  to the official `control_imotions.py` (`python/control_imotions.py` in
  github.com/imotions/iMotions-ApiExamples). Update the `format_*` helpers
  in `src/imotions_api.py` only — the `RemoteControlAPI` class is
  protocol-agnostic. Re-run this section after.

---

## 3. CVT test-mode dry run (markers only, no remote)

**Setup**
- [ ] `IMOTIONS_REMOTE_ENABLED=0` (default)
- [ ] iMotions open, recording started manually with respondent `PILOT01`

**Steps**
```bash
python src/cvt_task.py
```
- Participant ID: `PILOT01`
- Difficulty order: high → low
- Test mode: checked

**Pass criteria**
- [ ] Practice runs, then 2-minute test-mode CVT block
- [ ] iMotions timeline shows:
  - [ ] `cvt_practice_low`, `cvt_practice_high` scene pairs
  - [ ] `cvt_high_block`, `cvt_low_block` scene pairs
  - [ ] `cvt_period_1`, `cvt_period_2` discrete markers (test mode has 2 periods)
  - [ ] Many `cvt_signal_stim` and `cvt_nonsignal_stim` scene pairs
  - [ ] `cvt_response` discrete markers wherever you actually pressed the spacebar
- [ ] Each `cvt_response` description contains `rt=<ms>,trial=<n>,kind=signal` or `kind=nonsignal`
- [ ] JSON file written to `data/PILOT01/cvt_high_test_<ts>.json`
- [ ] Sidecar log written to `data/PILOT01/session_<ts>.imotions.log`
- [ ] No traceback in the terminal

**Note:** `cvt_task.py` (standalone) does not currently invoke run_session
orchestration, so the session-level scene and the sidecar log will not appear
unless you go through `src/run_session.py`. To exercise that path, use §4.

---

## 4. Full session dry run via run_session.py

**Setup**
- [ ] iMotions open with respondent `PILOT01` ready
- [ ] If `IMOTIONS_REMOTE_ENABLED=1`, do NOT pre-start the recording — the
      task will start it. Otherwise (default), start the recording manually first.

**Steps**
```bash
python src/run_session.py
```
- Participant ID: `PILOT01`
- Task order: CVT → PVT
- CVT difficulty order: high → low
- PVT difficulty order: high → low
- Test mode: checked

**Pass criteria**
- [ ] EEG baseline hold screen appears and waits for SPACE
- [ ] CVT runs (practice + 2 test-mode blocks with break) → 5-min inter-task break → PVT runs
- [ ] iMotions timeline shows:
  - [ ] One `session_PILOT01_<ts>` scene wrapping everything
  - [ ] `session_break_start` / `session_break_end` around the inter-task break
  - [ ] All CVT and PVT markers from §3
  - [ ] PVT markers: `pvt_high_block`/`pvt_low_block` scene pairs,
        `pvt_period_*`, `pvt_stim` scene pairs, `pvt_response`, `pvt_anticipatory`
        if you press too early
- [ ] Two task JSONs written under `data/PILOT01/`
- [ ] Sidecar log lists every marker call with monotonic timestamps
- [ ] If remote enabled: iMotions starts the recording right after the EEG
      baseline hold and stops it on session end

---

## 5. Failure-mode tests

### 5.1 iMotions not running
- [ ] Close iMotions
- [ ] Run §4 again
- [ ] **Pass**: Session completes normally. Console shows
      `iMotions Event API connect failed`. JSON files written. Sidecar log
      created but contains only the open header and the markers that *would*
      have been emitted (the `EventReceivingAPI` is disabled so no network
      attempts, but `LoggingMarkerClient` still records what was queued).

### 5.2 iMotions killed mid-session
- [ ] Start §4. After CVT begins, force-quit iMotions.
- [ ] **Pass**: Trial loop continues without stalling. Behavioral JSON is
      complete. Console shows `send failed` warnings. No traceback.

### 5.3 ESC mid-block
- [ ] Start §4. Press ESC during CVT.
- [ ] **Pass**: Session terminates. iMotions sees `scene_end` on the open
      block and `scene_end` on `session_<pid>_<ts>`. No dangling open scene
      in the timeline. Partial JSON written.

---

## 6. Timing sanity check

Pick one stimulus onset event during §4. In iMotions, note its iMotions-side
timestamp. In the sidecar log (`data/PILOT01/session_<ts>.imotions.log`), find
the matching `scene_start` line and note its `perf_counter` timestamp.

- [ ] The difference between corresponding markers across the session is stable
      (drift, not jitter). Sub-millisecond jitter on localhost TCP is expected.

A material discrepancy (>10 ms, consistent direction) would warrant adding the
post-flip `perf_counter` to the marker description before send-side — the task
code is already structured to allow this with a one-line change in the emitter.

---

## 7. Sign-off

- [ ] §1 passes
- [ ] §3 passes
- [ ] §4 passes
- [ ] §5.1, §5.2, §5.3 pass
- [ ] §2 attempted; result documented in `QUESTIONS_INTEGRATION.md` Q12
- [ ] If §2 wire format differs: update `format_run_study` / `format_cancel_study`
      and re-run §2 until green; commit the fix to the feature branch

Once all sections pass, the branch is ready to merge to `main`.

---

*Prepared by Jeff Roszell — May 2026*
