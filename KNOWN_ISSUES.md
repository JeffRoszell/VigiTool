# Known Issues

Tracked bugs and protocol mismatches identified in the current codebase.

## Critical Bugs

### 1. CVT: Shuffle destroys period structure
**File:** `src/digit_vigilance_WORKING.py:328`
Signals are carefully placed into 4 periods (5 per period), then `random.shuffle(self.trial_sequence)` scrambles the entire list. The `period` field no longer matches actual presentation order. All vigilance decrement analysis is meaningless.

### 2. CVT: z_score_approx is mathematically wrong
**File:** `src/digit_vigilance_WORKING.py:473-482`
The formula doesn't match any standard inverse normal approximation (Abramowitz & Stegun uses `t = sqrt(-2 * ln(p))`). Produces incorrect d' and criterion values — the core SDT metrics.

### 3. CVT: Responses accepted during blank screen
**File:** `src/digit_vigilance_WORKING.py:390-408`
`blank_screen()` records a miss/CR when participant didn't respond but never sets `self.responded = True`. Pressing spacebar during the blank interval records a duplicate trial with a bogus RT.

### 4. PVT: Anticipatory response doesn't cancel pending stimulus
**File:** `src/pvt_task_WORKING.py:219`
On anticipatory response, a new ISI is scheduled but the already-pending `present_stimulus` callback still fires. Creates two parallel stimulus chains running simultaneously.

## Protocol Mismatches

### 5. PVT: 10-minute duration instead of 24 minutes
**File:** `src/pvt_task_WORKING.py:43`
Protocol specifies two 24-minute sessions. Code uses 10 minutes.

### 6. PVT: No difficulty selection
Protocol specifies high/low difficulty conditions (500ms/1500ms ISI). PVT has no difficulty choice.

### 7. PVT: ISI range wrong
Protocol calls for fixed ISI (500ms or 1500ms depending on difficulty). Code uses random 1-10s ISI.

## Moderate Bugs

### 8. PVT: ESC messagebox blocks UI while timers keep running
**File:** `src/pvt_task_WORKING.py:462`
`messagebox.askyesno()` pauses interaction but `after()` callbacks continue firing. Stimuli pile up in the background. Also inconsistent with CVT which exits immediately.

### 9. Both tasks: Data saves to working directory
**Files:** `src/digit_vigilance_WORKING.py:517`, `src/pvt_task_WORKING.py:418`
Output should go to `data/<participant_id>/` per project spec. No participant ID input exists and files save to CWD.

### 10. Neither task cancels `after()` callbacks on exit
Pending `after()` calls keep firing after `end_task()` or `emergency_exit()`, which can cause errors on destroyed widgets.

### 11. analyze_data.py: Hardcoded path
**File:** `src/analyze_data.py:172`
Uses `/mnt/user-data/outputs` which won't work on any local machine.

## Minor Issues

### 12. Debug output left in production code
`print()` statements and visible debug/key-press labels remain in both tasks. Pre-commit hooks should catch these.

### 13. CVT: Falsy RT check
**File:** `src/digit_vigilance_WORKING.py:424`
`if rt else None` means a 0.0ms RT would incorrectly become `None`. Should be `if rt is not None`.
