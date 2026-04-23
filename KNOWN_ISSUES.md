# Known Issues

Tracked bugs and protocol mismatches identified in the codebase.

## Resolved (fixed in Phase 1 PsychoPy migration)

| # | Issue | File | Resolution |
|---|-------|------|------------|
| 1 | CVT: shuffle destroys period structure | legacy/digit_vigilance_WORKING.py:328 | Signals placed within each period, periods concatenated in order — no global shuffle |
| 2 | CVT: z_score_approx is mathematically wrong | legacy/digit_vigilance_WORKING.py:473 | Replaced with correct A&S 26.2.17 implementation + Hautus log-linear correction |
| 3 | CVT: responses accepted during blank screen (duplicate trials) | legacy/digit_vigilance_WORKING.py:390 | State machine with `responded` flag spans both stimulus and ISI phases |
| 4 | PVT: anticipatory response doesn't cancel pending stimulus | legacy/pvt_task_WORKING.py:219 | Time-based loop replaces callback chain entirely |
| 5 | PVT: 10-minute duration instead of 24 minutes | legacy/pvt_task_WORKING.py:43 | 24-minute block (2-minute test mode) |
| 6 | PVT: no difficulty selection | legacy/pvt_task_WORKING.py | High/low difficulty via launch dialog |
| 7 | PVT: ISI range wrong (random 1-10s instead of fixed 500/1500ms) | legacy/pvt_task_WORKING.py | Fixed blank ISI (500/1500ms) + separate random 1-10s fixation foreperiod |
| 8 | PVT: ESC messagebox blocks UI while timers keep running | legacy/pvt_task_WORKING.py:462 | ESC checked in every poll loop, returns immediately with guaranteed save via `finally` |
| 9 | Both: data saves to working directory, no participant ID | legacy/* | Data saves to `data/<participant_id>/` via launch dialog |
| 10 | Neither task cancels `after()` callbacks on exit | legacy/* | No callbacks — time-based polling loops exit cleanly |
| 11 | analyze_data.py: hardcoded path | legacy/analyze_data.py:172 | Not yet updated (Phase 4) |
| 12 | Debug output left in production code | legacy/* | No print statements or debug labels in src/ |
| 13 | CVT: falsy RT check (`if rt` vs `if rt is not None`) | legacy/digit_vigilance_WORKING.py:424 | Explicit `if rt_ms is not None` throughout |

---

## Open

### PVT foreperiod range unconfirmed
Per REQUIREMENTS §6, the 1–10s foreperiod range needs confirmation with Dr. Poltavski.
Currently implemented as 1–10s (`FOREPERIOD_RANGE` in `src/pvt_task.py`).

### PVT stimulus size unconfirmed
Red circle radius is set to 0.08 norm units (~8% of screen height).
Exact size to be confirmed with Dr. Poltavski (REQUIREMENTS §6).

### analyze_data.py not yet updated
`legacy/analyze_data.py` has a hardcoded `/mnt/user-data/outputs` path.
Will be updated in Phase 4 to point to `data/<participant_id>/`.

### PsychoPy 2026.1.3 DlgFromDict bug
`DlgFromDict.show()` indexes `self.data` (a list) with a string key when
`copyDict=False`. Worked around in both tasks with `copyDict=True` and reading
from `dlg.dictionary`. Upstream bug — track if fixed in future PsychoPy releases.
