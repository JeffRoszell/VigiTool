# Known Issues

Tracked bugs and protocol mismatches identified in the codebase.

## Resolved (fixed in Phase 1 PsychoPy migration)

| # | Issue | File | Resolution |
|---|-------|------|------------|
| 1 | CVT: shuffle destroys period structure | legacy/digit_vigilance_WORKING.py:328 | Signals placed within each period, periods concatenated in order — no global shuffle |
| 2 | CVT: z_score_approx is mathematically wrong | legacy/digit_vigilance_WORKING.py:473 | Replaced with correct A&S 26.2.17 implementation + Hautus log-linear correction |
| 3 | CVT: responses accepted during blank screen (duplicate trials) | legacy/digit_vigilance_WORKING.py:390 | State machine with `responded` flag spans both stimulus and ISI phases |
| 4 | PVT: anticipatory response doesn't cancel pending stimulus | legacy/pvt_task_WORKING.py:219 | Time-based loop replaces callback chain entirely |
| 5 | *(retracted — see below)* | | |
| 6 | *(retracted — see below)* | | |
| 7 | *(retracted — see below)* | | |
| 8 | PVT: ESC messagebox blocks UI while timers keep running | legacy/pvt_task_WORKING.py:462 | ESC checked in every poll loop, returns immediately with guaranteed save via `finally` |
| 9 | Both: data saves to working directory, no participant ID | legacy/* | Data saves to `data/<participant_id>/` via launch dialog |
| 10 | Neither task cancels `after()` callbacks on exit | legacy/* | No callbacks — time-based polling loops exit cleanly |
| 11 | analyze_data.py: hardcoded path | legacy/analyze_data.py:172 | Not yet updated (Phase 4) |
| 12 | Debug output left in production code | legacy/* | No print statements or debug labels in src/ |
| 13 | CVT: falsy RT check (`if rt` vs `if rt is not None`) | legacy/digit_vigilance_WORKING.py:424 | Explicit `if rt_ms is not None` throughout |

---

## Retracted — not defects

### Rows 5, 6, 7 — the legacy PVT was right

Retracted September 2026. These three rows recorded the legacy PVT's 10-minute
duration, absence of difficulty conditions, and random 1–10 s intervals as defects,
and Phase 1 "fixed" them into two 24-minute high/low blocks with a fixed 500/1500 ms
ISI. The Co-PI has since designated the Millisecond Inquisit Perceptual Vigilance Task
(keyboard) manual as the authoritative PVT specification, and the manual specifies
exactly the behaviour that was removed: a single 10-minute block, no difficulty
factor, and intervals drawn from the discrete 1–10 s set.

The current implementation therefore converges on the legacy behaviour — but *by way
of the manual*, not by reverting. `legacy/pvt_task_WORKING.py` stays frozen: it has no
iMotions markers, no eye-tracker hooks, no period metrics, and no JSON schema.

The high/low difficulty factor was never wrong in itself; it belongs to the **CVT**,
where it remains.

---

## Open

### PVT RT feedback duration — manual applied over an earlier decision
The manual specifies 500 ms; a June 2026 decision set 1 s. The manual was applied
under the tie-breaker rule. Confirm with Dr. Gupta that the 1 s value was not a
deliberate deviation (REQUIREMENTS §7).

### PVT period structure unconfirmed
The manual defines no period structure, so the tie-breaker rule does not apply.
4 × 2.5 min adopted provisionally for comparability with the CVT's four-period
vigilance decrement analysis (REQUIREMENTS §7).

### Session duration may require an IRB protocol modification
The PVT drops from roughly 48 minutes plus a break to a single 10-minute block,
changing the participant time commitment stated under IRB #0007078. Confirm with the
PI whether a modification must be filed before the next run (REQUIREMENTS §7).

### Mixed-protocol data under data/
PVT filenames no longer carry a difficulty, so a naive glob mixes pre-change 24-minute
two-block sessions with 10-minute single-block ones. `metadata.schema_version`
discriminates: absent means v1. Pre-v2 PVT data is a **different protocol**, not a
covariate, and must not be pooled.

### Old-schema sample retained
`data/12/pvt_low_test_20260422_213556.json` is a real v1 artifact and is kept
unmodified. It is not a fixture; do not rewrite it to the v2 shape.

### analyze_data.py not yet updated
`legacy/analyze_data.py` has a hardcoded `/mnt/user-data/outputs` path.
Will be updated in Phase 4 to point to `data/<participant_id>/`.

### PsychoPy 2026.1.3 DlgFromDict bug
`DlgFromDict.show()` indexes `self.data` (a list) with a string key when
`copyDict=False`. Worked around in both tasks with `copyDict=True` and reading
from `dlg.dictionary`. Upstream bug — track if fixed in future PsychoPy releases.
