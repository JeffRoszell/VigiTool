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

- **Protocol**: TCP (preferred over UDP; UDP noted as "not well supported" in third-party implementations)
- **Port**: 8089 (iMotions default)
- **Architecture**: iMotions acts as the **server**; the task script is the **client**
- **Setup required in iMotions**: Global Preferences → API → Enable event reception + Use TCP
- **Python socket**: `socket.socket(socket.AF_INET, socket.SOCK_STREAM)`, connect to `('127.0.0.1', 8089)`

### 5.2 Marker Format

Two marker types are supported. Format is semicolon-delimited, terminated with `\r\n`:

| Type | Format |
|------|--------|
| Discrete (point-in-time) | `M;2;;;label;;S;I\r\n` |
| Range start | `M;2;;;label;;S;I\r\n` |
| Range end | `M;2;;;label;;E;I\r\n` |

These formats are cross-referenced from the iMotions 7.0 Programming Guide and consistent with the marker format in `MIGRATION_PLAN.md`. Field definitions for the full semicolon-delimited structure are not publicly documented — they require access to the iMotions Help Center (login required at `my.imotions.com`).

### 5.3 Research Limitations

- Full iMotions API documentation is behind a login at `my.imotions.com` — not publicly accessible
- The official iMotions + PsychoPy integration blog post returns 404 (as of April 2026)
- A PsychoPy community thread asking for a working iMotions marker example has no accepted answer (last checked April 2026)
- No public Python implementation with confirmed working format was found
- **Action required**: Retrieve the Programming Guide PDF from the lab machine (typically installed alongside iMotions) and confirm the exact field structure and any version-specific differences

### 5.4 Sources

- [iMotions API overview](https://imotions.com/products/imotions-lab/developers/api/)
- [iMotions 7.0 Programming Guide (Scribd — requires account)](https://www.scribd.com/document/429363242/IMotions-7-0-Programming-Guide-January-2018)
- [PsychoPy forum — iMotions marker question (unanswered)](https://discourse.psychopy.org/t/trigger-markers-in-imotions-through-psychopy-connect-to-imotions-api/32571)
- [GitHub: lochiego/iomotions — Python TCP wrapper](https://github.com/lochiego/iomotions)
- [GitHub: ltcmdrkeen/imotions-web-bridge — JS→TCP bridge with marker format examples](https://github.com/ltcmdrkeen/imotions-web-bridge)

---

## 6. Open Items
- Retrieve iMotions Programming Guide PDF from lab machine to confirm exact marker field definitions
- All items in `QUESTIONS_INTEGRATION.md` must be resolved before full implementation
- Hardware access needed for testing
- May require non-standard-library Python packages (pylsl, tobii_research, pyserial)

---

*Prepared by Jeff Roszell — March 2026*
*iMotions API research added April 2026*
