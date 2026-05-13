# Requirements Specification — EEG & Eye-Tracking Integration
## Vigilance Task Suite — Poltavski Lab, UND

### Study Reference
- **IRB**: #0007078
- **PI**: Dmitri Poltavski
- **Co-PI**: Dr. Utkarsh Gupta

---

## Status: Planning Phase
This is a separate development phase from the core CVT/PVT task software. Implementation depends on answers from `QUESTIONS_INTEGRATION.md`.

---

## 1. Systems to Integrate

### 1.1 B-Alert X-24 (EEG)
- Wireless wet electrode system, 20 channels, International 10-20 layout
- Sampled at 256 Hz with online notch and low-pass FIR filtering
- Software: B-Alert Live
- Needs event markers synchronized to task events for ERP/spectral analysis

### 1.2 Tobii Pro Fusion (Eye-Tracking)
- 120 Hz sampling rate
- Software: Tobii Pro Lab
- 9-point calibration, participant seated 60 cm from tracker
- Needs event markers for gaze analysis aligned to task events

### 1.3 Smarteye
- Role in study TBD (see questions doc)
- May need event markers depending on role

---

## 2. Event Marker Requirements (Preliminary)

The task software should be architected to support an event marker interface that can be implemented later. Suggested approach:

### 2.1 Internal Event Log
Even before hardware integration, the task software should maintain a high-precision internal event log with:
- Event type (stimulus_onset, stimulus_offset, response, block_start, block_end, period_transition)
- Timestamp (ms precision, relative to block start)
- Trial metadata (signal/non-signal, quadrant, stimulus value, difficulty)

### 2.2 Marker Interface (Future)
- Abstract marker interface in the code that can be connected to:
  - LSL (Lab Streaming Layer) — likely candidate for B-Alert
  - Tobii Pro SDK — for Tobii Pro Fusion
  - Serial/TTL — if hardware supports it
  - UDP — if network-based
- The interface should be pluggable so integration doesn't require rewriting task logic

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

iMotions serves as the synchronization hub for all biosensors (B-Alert, Tobii, Smarteye). The task software communicates with iMotions via its external API rather than integrating with each sensor SDK directly.

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

## 6. Open Items
- Remaining items in `QUESTIONS_INTEGRATION.md` (Smarteye role, timing precision, lab specs, installed iMotions version) must be resolved before full implementation
- Hardware access on the lab machine needed for end-to-end testing
- No non-standard Python packages required for the marker path — stdlib `socket` is sufficient

## 7. File-Import Fallback

If live marker streaming proves infeasible (network issue, version mismatch, license limitation), iMotions supports post-hoc data import:

- **Post Import Data**: externally recorded data can be uploaded into a finished iMotions recording for joint analysis
- **CSV import**: sensor data exports/imports support comma, tab, or semicolon delimiters
- **Trade-off**: post-hoc alignment relies on shared timestamps rather than network-delivered markers, so temporal precision is bounded by clock skew between machines

This path is documented as a contingency only — the live API is the preferred integration.

---

*Prepared by Jeff Roszell — March 2026*
*iMotions API research added April 2026*
*Updated with official iMotions reference code (Feb 2026 release) — May 2026*
