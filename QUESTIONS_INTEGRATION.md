# Technical Questions — EEG & Eye-Tracking Integration
## Vigilance Task Software Development — IRB #0007078

These questions relate to the planned integration of the vigilance task software with the B-Alert X-24 EEG system, Tobii Pro Fusion eye-tracker, and Smarteye platform. This integration is a separate development phase from the core task software.

> **Research note (May 2026)**: iMotions publishes [official PsychoPy + Python reference code on GitHub](https://github.com/imotions/iMotions-ApiExamples) (updated Feb 2026). This confirms the marker wire format (correcting the April 2026 entry) and resolves questions 1, 2, 4, 5, 7, and 11. See `REQUIREMENTS_INTEGRATION.md §5` for current findings.
>
> **Research note (April 2026)**: iMotions serves as the integration hub — all biosensors sync through it. The task software sends TCP markers to iMotions on port 8089; iMotions handles synchronization with B-Alert, Tobii, and Smarteye internally.

---

### System Roles & Protocols

1. **B-Alert X-24**: What marker/event protocol does the B-Alert system expect from external software? (LSL stream, TTL pulse via parallel port, serial port, UDP, etc.)
   > **Resolved**: B-Alert is integrated by iMotions; the task software does not communicate with it directly.

2. **Tobii Pro Fusion**: Does Tobii Pro Lab software accept external event markers? If so, via what protocol? (LSL, SDK API call, etc.)
   > **Resolved**: Tobii is integrated by iMotions; no direct Tobii SDK integration required.

3. **Smarteye**: What is Smarteye's role in the study alongside the Tobii? Is it a redundant/complementary eye-tracking system, or does it serve a different purpose (e.g., head tracking)? Does it also need event markers from the task software?
   > *Still open*: Confirm with PI whether Smarteye routes through iMotions or needs separate handling.

4. **Single computer or multiple?** Will the task software, B-Alert, Tobii, and Smarteye all run on the same machine, or across separate machines on a local network?
   > **Resolved (for the marker path)**: The task software and iMotions must run on the same machine — markers go to `localhost:8089`. Where the biosensor acquisition units physically connect (USB to the iMotions machine vs. separate acquisition PCs) does not affect our software.

5. **Existing synchronization**: Is there already a synchronization method between the B-Alert and Tobii/Smarteye systems, or will the task software be the common time reference?
   > **Resolved**: iMotions is the synchronization hub. The task software sends markers; iMotions timestamps them on its internal clock and aligns all sensor streams to that clock.

### Events to Mark

6. **What events should be marked?** Suggested list — please confirm or modify:
   - Block start / block end
   - Period transitions (every 6 minutes)
   - Each stimulus onset
   - Each stimulus offset
   - Each participant response (with timestamp)
   - Signal vs. non-signal trial type (CVT)
   - Practice start / practice end
   - Difficulty condition identifier

7. **Marker format**: Do the systems expect numeric codes (e.g., marker 1 = stimulus onset, marker 2 = response), string labels, or both?
   > **Resolved**: iMotions accepts string labels in semicolon-delimited messages — see `REQUIREMENTS_INTEGRATION.md §5.2` for the full format. Confirmed from official Feb 2026 reference code.

8. **Timing precision requirements**: What temporal precision is needed for markers? (e.g., <1 ms, <5 ms, <10 ms)
   > *Still open*: Confirm with PI. TCP marker delivery over localhost is typically <1 ms; iMotions timestamps markers on receipt at the application layer.

### Hardware & Software Environment

9. **Lab computer specs**: What OS and hardware is in Research Room B347D? This affects which marker protocols are feasible (e.g., parallel port TTL requires specific hardware).
   > *Low priority*: TCP over localhost has no special hardware requirements. Still worth confirming the OS (PsychoPy and iMotions both run on Windows, which is assumed).

10. **Software versions**: What versions of B-Alert Live, Tobii Pro Lab, and Smarteye software are installed?
    > *Still open* — and: **What version of iMotions is installed?** The reference code is from the current iMotions repo (Feb 2026); the marker format has been stable across recent versions but worth confirming.

11. **Existing Python packages**: Are there any Python packages already installed on the lab machine for interfacing with these systems (e.g., `pylsl`, `tobii_research`)?
    > **Resolved**: Not needed. Only Python's built-in `socket` module is required for the marker path.

---

### Workflow & Failure Handling (new — for PI)

These questions arose after confirming the live API is viable. They affect study workflow and data quality, not just the implementation.

12. **Who starts and stops the iMotions recording?** Two options:
    - (a) RA clicks "Start" in iMotions, then launches `run_session.py`. Task software only sends markers into an already-running recording.
    - (b) `run_session.py` uses the Remote Control API (port 8087) to start the iMotions study automatically when the participant clicks Continue.
    > Option (a) is simpler and lower-risk; option (b) reduces RA workload and timing variability. Confirm preference.

13. **Per-participant iMotions setup**: Will each participant be a new "respondent" inside one shared iMotions study, or will a new iMotions study be created per session? This determines whether the task script needs to pass a respondent name through the Remote Control API or whether the RA enters it in iMotions before launching the task.

14. **Stimulus event granularity for markers**: For each CVT trial, should the marker stream include:
    - (a) only stimulus onset (and the local JSON has the rest)
    - (b) onset + offset as a paired scene start/end ("range marker")
    - (c) onset, offset, and a separate response marker
    > More markers = more granular ERP analysis but a denser, harder-to-read iMotions timeline. Recommend (a) for non-signal trials and (c) for signal trials, but confirm.

15. **Signal vs. non-signal labels in CVT markers**: Should the marker name distinguish trial type (`cvt_signal_onset` vs. `cvt_nonsignal_onset`)? This makes ERP epoching trivial but reveals trial type in the iMotions timeline (acceptable for offline analysis; only matters if anyone observes the recording live).

16. **Failure tolerance**: If iMotions is not running, or the TCP connection drops mid-block, should the task:
    - (a) abort the block immediately (preserves biosensor coverage but loses behavioral data)
    - (b) continue with a warning logged locally (preserves behavioral data; biosensor alignment may be partially recoverable post-hoc)
    > Recommend (b) — local JSON is the primary record for behavioral metrics regardless of biosensor state.

17. **Timing-precision target**: What alignment precision is required between the task markers and the EEG/eye-tracking streams for the analyses planned (Engagement Index, Frontal Theta, fixation/saccade events)? This sets the threshold for whether the localhost-TCP path (typically sub-ms) is sufficient or whether we should add a redundant hardware trigger.

18. **Recording continuity**: The Remote Control API starts/stops *all sensors at once* — there is no public way to toggle EEG vs. eye-tracking independently. Should the iMotions recording be:
    - (a) one continuous recording for the whole session (EEG + eye-tracking active during practice, breaks, and both tasks), or
    - (b) segmented — start at the beginning of CVT, stop after, restart for PVT?
    > Option (a) is simpler and gives a continuous EEG baseline across the session; option (b) produces smaller, task-scoped files.

19. **Calibration timing in the session**: Eye-tracker calibration (Tobii 9-point) and B-Alert impedance checks happen through iMotions' own UI before recording starts — PsychoPy can't trigger them mid-session. Confirm the intended session order:
    - RA seats participant → RA runs Tobii calibration + B-Alert impedance in iMotions → RA launches `run_session.py` → app sends EEG-baseline hold screen → recording proceeds.
    > Is re-calibration ever needed between blocks (e.g., if the participant shifts position)? If so, the app needs an explicit pause point where the RA can re-enter iMotions.

20. **iMotions study definition ownership**: Using the Remote Control API requires an iMotions study definition (sensor list, recording settings) to already exist by name. Who builds and maintains it? Suggested model: one canonical "Vigilance_CVT_PVT" study, defined once, with a new respondent added per participant. Confirm — and confirm who has admin rights in iMotions to create/edit the study.

---

*Prepared by Jeff Roszell — March 2026*
*Updated with iMotions API research findings — April 2026*
*Resolved 6 of 11 questions and added workflow questions for PI — May 2026*
