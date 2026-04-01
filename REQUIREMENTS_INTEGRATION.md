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

## 5. Open Items
- All items in `QUESTIONS_INTEGRATION.md` must be resolved before implementation
- Hardware access needed for testing
- May require non-standard-library Python packages (pylsl, tobii_research, pyserial)

---

*Prepared by Jeff Roszell — March 2026*
