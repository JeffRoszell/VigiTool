# Requirements Specification — EEG & Eye-Tracking Integration
## Vigilance Task Suite — Poltavski Lab, UND

### Study Reference
- **IRB**: #0007078
- **PI**: Dmitri Poltavski
- **Co-PI**: Dr. Utkarsh Gupta

---

## Status: Phase 2 Implemented (Pending Lab E2E)
The marker streaming path is implemented and unit-tested. The Remote Control
client is implemented behind a feature flag (default off). The remaining work
is end-to-end validation on the lab machine — see `docs/imotions_e2e_test_plan.md`.

---

## 1. Systems to Integrate

### 1.1 B-Alert X-24 (EEG)
- Wireless wet electrode system, 20 channels, International 10-20 layout
- Sampled at 256 Hz with online notch and low-pass FIR filtering
- Software: B-Alert Live
- Needs event markers synchronized to task events for ERP/spectral analysis

### 1.2 Smarteye (Eye-Tracking)
- **PI decision (June 2026)**: Smarteye is the study's eye tracker, integrated
  through iMotions — **no Tobii integration** (the Tobii Pro Fusion described
  in earlier drafts is not used)
- Calibration runs through iMotions' UI; recalibration required after every
  5-minute break (see §6.4 session-level markers)
- Receives task event markers via iMotions like all other sensors

---

## 2. Event Marker Requirements (Preliminary)

The task software should be architected to support an event marker interface that can be implemented later. Suggested approach:

### 2.1 Internal Event Log
Even before hardware integration, the task software should maintain a high-precision internal event log with:
- Event type (stimulus_onset, stimulus_offset, response, block_start, block_end, period_transition)
- Timestamp (ms precision, relative to block start)
- Trial metadata (signal/non-signal, quadrant, stimulus value, difficulty)

### 2.2 Marker Interface (Implemented — May 2026)
- Implemented as `src/imotions_api.py` (`EventReceivingAPI`, `RemoteControlAPI`,
  `LoggingMarkerClient`, `NoOpMarkerClient`) and per-task emitter classes
  (`CvtMarkerEmitter`, `PvtMarkerEmitter`) that own the label-string contract.
- Stdlib `socket` + `threading` + `queue` only — no new runtime deps.
- The task functions accept a `marker_client` argument and default to a no-op,
  so tests and dev runs continue to work without iMotions.
- LSL / Tobii SDK / TTL / UDP are no longer in scope: all biosensor sync runs
  through iMotions.

---

## 3. EEG Measures of Interest (For Context)
These inform what events need precise marking:

- **Engagement Index** (EI): Beta / (Alpha + Theta) at Cz, P3, P4, Pz
- **Fatigue Index** (FI): (Alpha + Theta) / Beta at same sites
- **Frontal Engagement Index** (fEI): same ratio at F3, F4, F7, F8
- **Frontal Theta Index**: at Fp1, Fp2, F3, F4
- **Task Load Index** (TLI): frontal midline theta (Fz) / posterior slow alpha (Pz)
- **B-Alert cognitive state classification** algorithms

---

## 4. Eye-Tracking Measures of Interest (For Context)
- Gaze transition entropy (GTE)
- Fixation duration and variability
- Saccade amplitude and rate
- Pupil diameter (cognitive effort/arousal)

---

## 5. iMotions API — Research Findings

iMotions serves as the synchronization hub for all biosensors (B-Alert, Smarteye). The task software communicates with iMotions via its external API rather than integrating with each sensor SDK directly.

### 5.1 Connection

iMotions exposes **two separate TCP APIs**, each on its own port. Both run on the same machine as iMotions and accept connections from localhost.

| API | Port | Purpose |
|-----|------|---------|
| **Event Receiving API** | 8089 | Send markers and custom sensor data into the running recording |
| **Remote Control API** | 8087 | Start/stop studies, advance slides, query status |

For this project the **Event Receiving API (8089)** is the primary channel — it is where stimulus/response markers are sent. The Remote Control API is optional and may be used to have the session orchestrator command iMotions to begin recording (instead of an RA clicking Start).

- **Protocol**: TCP (UDP is supported but TCP is recommended)
- **Architecture**: iMotions is the **server**; the task script is the **client**
- **Setup required in iMotions**: Global Settings → API → Enable the relevant API, choose TCP, confirm the port
- **Python socket**: `socket.socket(socket.AF_INET, socket.SOCK_STREAM)`, connect to `('127.0.0.1', 8089)`
- **Encoding**: UTF-8

### 5.2 Marker Format (Event Receiving API)

Markers are semicolon-delimited and terminated with `\r\n`. There are three marker shapes:

| Marker shape | Format |
|--------------|--------|
| Discrete (point-in-time) | `M;2;;;<name>;<description>;D;\r\n` |
| Scene start — image | `M;2;;;<name>;<description>;N;I\r\n` |
| Scene start — video | `M;2;;;<name>;<description>;N;V\r\n` |
| Scene end | `M;2;;;<name>;;E;\r\n` |

Field positions (1-indexed):

| # | Value | Meaning |
|---|-------|---------|
| 1 | `M` | Message type — marker |
| 2 | `2` | API version |
| 3 | *(empty)* | Reserved |
| 4 | *(empty)* | Reserved |
| 5 | `<name>` | Event label (e.g. `stimulus_onset`, `period_1`) |
| 6 | `<description>` | Optional free-text description |
| 7 | `D` / `N` / `E` | Type code — **D**iscrete, sce**N**e start, sce**N**e **E**nd |
| 8 | `I` / `V` / *(empty)* | Media hint for scene starts: **I**mage or **V**ideo. Empty on discrete and end markers |

Scene start/end pairs use the same `<name>` to associate them, giving a duration ("range") marker — appropriate for period boundaries, full blocks, and stimulus on/off pairs.

Names are sanitized of internal semicolons by the reference implementation (semicolons become underscores), since `;` is the field delimiter.

### 5.3 Reference Implementation

iMotions publishes official, MIT-licensed Python example code on GitHub:
**[github.com/imotions/iMotions-ApiExamples](https://github.com/imotions/iMotions-ApiExamples)** (last updated Feb 2026).

Relevant files:
- `python/send_to_imotions.py` — `SendToImotions` class implementing the Event Receiving API. Context-managed TCP socket with `marker()`, `start_scene_image()`, `start_scene_video()`, `end_scene()` methods. Suitable as the basis for our `src/imotions_markers.py`.
- `python/control_imotions.py` — `ControlImotions` class for the Remote Control API on port 8087 (run_study, next_stimulus, cancel_study, status, etc.).
- `psychopy/example.py` — PsychoPy experiment that opens a socket to `127.0.0.1:8089` and sends discrete markers from `Begin Routine` blocks. Demonstrates the canonical PsychoPy → iMotions pattern.

The repo README confirms our wire-format invariants: semicolon-delimited fields, `\r\n` terminator, UTF-8 encoding. Troubleshooting log: `C:\ProgramData\iMotions\Lab_XG\Log\imotions.log`.

### 5.4 Sources

**Authoritative (current):**
- [iMotions-ApiExamples — official Python + PsychoPy code (Feb 2026)](https://github.com/imotions/iMotions-ApiExamples)
- [iMotions API page](https://imotions.com/products/imotions-lab/developers/api/)
- [iMotions API Programmer's Guide (Help Center — login-gated)](https://help.imotions.com/docs/imotions-api-programming-guide)
- [iMotions API Overview (Help Center — login-gated)](https://help.imotions.com/docs/an-introduction-to-the-api)

**Historical / background:**
- [iMotions 7.0 Programming Guide (Scribd, 2018)](https://www.scribd.com/document/429363242/IMotions-7-0-Programming-Guide-January-2018) — superseded; field 7 differs from current code (showed `S` instead of `D`/`N`)
- [GitHub: lochiego/iomotions](https://github.com/lochiego/iomotions) — third-party Python wrapper, predates official examples
- [GitHub: ltcmdrkeen/imotions-web-bridge](https://github.com/ltcmdrkeen/imotions-web-bridge) — JS→TCP bridge

### 5.5 May 2026 Update — Corrections to April 2026 Notes

The April 2026 marker-format table in this section was wrong. It listed discrete markers as `M;2;;;label;;S;I\r\n` based on the 2018 7.0 Programming Guide cross-referenced via third-party sources. The official Feb 2026 reference implementation shows the discrete type code is **`D`** (not `S`) and scene starts use **`N`** with a media-type indicator in field 8. The §5.2 table above reflects the corrected format. No code has been written against the incorrect format yet.

---

## 6. Implementation Notes (Phase 2 — May 2026)

### 6.1 Modules

| File | Purpose |
|------|---------|
| `src/imotions_api.py` | `EventReceivingAPI` (8089), `RemoteControlAPI` (8087), `LoggingMarkerClient`, `NoOpMarkerClient`, wire-format helpers |
| `src/imotions_config.py` | Env-var driven config (host, ports, feature flags, study name) |
| `src/cvt_task.py` | Adds `CvtMarkerEmitter`; `run_task` / `run_practice` / `run_full_session` accept an `emitter` / `marker_client` argument |
| `src/pvt_task.py` | Adds `PvtMarkerEmitter`; same wiring pattern as CVT |
| `src/run_session.py` | Opens one continuous Event Receiving connection across the whole session, optionally opens Remote Control, wraps everything in `session_<pid>_<ts>` scene, tears down in `finally` |

### 6.2 Design choices (locked with PI, May 2026)

| Decision | Choice |
|----------|--------|
| Recording continuity (Q18) | One continuous Event Receiving recording across the whole session |
| Remote Control (Q12) | Built but feature-flagged off (default); RA starts iMotions manually until verified |
| Marker granularity per trial (Q14) | Most granular: `scene_start` (onset) + `scene_end` (offset) + discrete `response` |
| Signal vs non-signal labels (Q15) | Distinguish (`cvt_signal_stim`, `cvt_nonsignal_stim`) |
| Failure tolerance (Q16) | Continue with warning logged locally; behavioral JSON is the primary record — reconfirmed by PI June 2026 (acceptable while disconnects stay rare) |
| Error labeling (Q6, June 2026) | Per-trial outcome markers; misses = `*_error_omission`, false alarms / anticipatory = `*_error_commission` |
| Recalibration (Q19, June 2026) | RA hold screen + `recalibration_start/end` markers after every 5-min break |
| Eye tracking (Q3, June 2026) | Smarteye via iMotions only — no Tobii integration |
| Timing precision (Q17, June 2026) | Sub-millisecond sufficient; localhost TCP, no hardware trigger |
| Recording start (Q12, June 2026) | Confirmed option (a): RA starts iMotions; Remote Control flag stays off |

### 6.3 Async, fail-soft sender

`EventReceivingAPI` runs a daemon thread + bounded `queue.Queue` (default 8192 slots).
Marker calls in the trial loop enqueue bytes and return; the worker drains and
`sendall`s. Any socket error (connect or send) flips `enabled=False`, closes the
socket, and silently drops subsequent calls. The trial loop never sees an exception.

### 6.4 Per-trial marker label set

CVT:
- `cvt_<difficulty>_block` — scene pair (per block)
- `cvt_practice_<difficulty>` — scene pair (each practice segment)
- `cvt_period_<n>` — discrete, on first trial of each new period
- `cvt_signal_stim` / `cvt_nonsignal_stim` — scene pair (per trial)
- `cvt_response` — discrete with `rt=<ms>,trial=<n>,kind=signal|nonsignal`
- `cvt_hit` / `cvt_correct_rejection` / `cvt_error_omission` (miss) /
  `cvt_error_commission` (false alarm) — discrete outcome marker per scored
  trial, description `outcome=...,trial=<n>,period=<p>,rt=<ms|none>`
  (PI decision June 2026)

PVT:
- `pvt_<difficulty>_block` — scene pair (per block)
- `pvt_period_<n>` — discrete, on first trial of each new period
- `pvt_stim` — scene pair (per trial; description `trial=<n>,period=<p>`)
- `pvt_response` — discrete with `rt=<ms|none>,type=valid|lapse|anticipatory|timeout,trial=<n>`
- `pvt_anticipatory` — discrete on pre-stim press, `phase=isi|foreperiod`,
  accompanied by `pvt_error_commission` (`type=anticipatory,phase=...`)
- `pvt_error_omission` — discrete after lapse/timeout responses,
  `type=lapse|timeout,rt=<ms|none>,trial=<n>` (PI decision June 2026)
- `pvt_error_commission` — discrete after anticipatory responses,
  `type=anticipatory,rt=<ms>,trial=<n>`

Session-level:
- `session_<pid>_<ts>` — scene pair wrapping the whole run
- `session_break_start` / `session_break_end` — discrete around the 5-min inter-task break
- `recalibration_start` / `recalibration_end` — discrete pair around the RA
  eye-tracking recalibration hold that follows **every** 5-min break
  (between blocks within a task and between tasks; PI decision June 2026)

### 6.5 Configuration

Env vars (see `src/imotions_config.py`):
- `IMOTIONS_ENABLED` (default `1`)
- `IMOTIONS_REMOTE_ENABLED` (default `0`)
- `IMOTIONS_HOST` (default `127.0.0.1`)
- `IMOTIONS_EVENT_PORT` (default `8089`)
- `IMOTIONS_REMOTE_PORT` (default `8087`)
- `IMOTIONS_STUDY_NAME` (default `Vigilance_CVT_PVT`)

### 6.6 Sidecar log

`run_session` writes a per-session marker log to
`data/<pid>/session_<ts>.imotions.log`. Every marker call is recorded with a
`perf_counter` timestamp regardless of whether iMotions actually received it —
useful for post-hoc debugging of clock skew or dropped markers.

---

## 7. Open Items
- **iMotions / B-Alert Live / Smarteye software versions on lab machine**
  (Q10): PI to confirm after reconnecting with James.
- **iMotions study setup**: shared `Vigilance_CVT_PVT` study to be built with
  the PI after James's handover (joint call being scheduled).
- Hardware access on the lab machine needed for end-to-end testing — see
  `docs/imotions_e2e_test_plan.md`.
- **Remote Control wire format** (low priority — client is dormant by PI
  decision June 2026): the documented `R;1;;<CMD>;...;\r\n` shape would need
  verification against the official reference before ever enabling
  `IMOTIONS_REMOTE_ENABLED=1`. Only the `format_*` helpers would change.

## 8. File-Import Fallback

If live marker streaming proves infeasible (network issue, version mismatch, license limitation), iMotions supports post-hoc data import:

- **Post Import Data**: externally recorded data can be uploaded into a finished iMotions recording for joint analysis
- **CSV import**: sensor data exports/imports support comma, tab, or semicolon delimiters
- **Trade-off**: post-hoc alignment relies on shared timestamps rather than network-delivered markers, so temporal precision is bounded by clock skew between machines

This path is documented as a contingency only — the live API is the preferred integration.

---

*Prepared by Jeff Roszell — March 2026*
*iMotions API research added April 2026*
*Updated with official iMotions reference code (Feb 2026 release) — May 2026*
