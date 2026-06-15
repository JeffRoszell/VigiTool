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
   > **Resolved (June 2026, PI)**: Smarteye devices + iMotions only — **no Tobii integration required**. Smarteye routes through iMotions; no separate handling by the task software.

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
   > **Resolved (June 2026, PI)**: List confirmed, **including stimulus offset**, plus explicit error labeling: misses are marked `*_error_omission` and false alarms / anticipatory presses `*_error_commission`. Implemented as per-trial outcome markers in `CvtMarkerEmitter.outcome` and `PvtMarkerEmitter.error_outcome`.

7. **Marker format**: Do the systems expect numeric codes (e.g., marker 1 = stimulus onset, marker 2 = response), string labels, or both?
   > **Resolved**: iMotions accepts string labels in semicolon-delimited messages — see `REQUIREMENTS_INTEGRATION.md §5.2` for the full format. Confirmed from official Feb 2026 reference code.

8. **Timing precision requirements**: What temporal precision is needed for markers? (e.g., <1 ms, <5 ms, <10 ms)
   > **Resolved (June 2026, PI)**: Sub-millisecond synchronization is sufficient. Localhost TCP meets this; **no hardware trigger needed**.

### Hardware & Software Environment

9. **Lab computer specs**: What OS and hardware is in Research Room B347D? This affects which marker protocols are feasible (e.g., parallel port TTL requires specific hardware).
   > *Low priority*: TCP over localhost has no special hardware requirements. Still worth confirming the OS (PsychoPy and iMotions both run on Windows, which is assumed).

10. **Software versions**: What versions of B-Alert Live, Tobii Pro Lab, and Smarteye software are installed?
    > **Resolved (June 2026, U. Gupta)**: iMotions **11.1.5**; B-Alert Live **3.1x**
    > (renewed ABM license being activated, then updated to the current build).
    > Tobii Pro Lab no longer applies (Smarteye only). Our marker/Remote Control
    > wire format is unchanged across the iMotions 11.1.x line — the code was
    > validated against the Feb 2026 reference implementation (= 11.1.0), and the
    > published 11.1.1–11.1.3 release notes change no API surface we use. Three
    > items move to the lab E2E checklist (`docs/imotions_e2e_test_plan.md` §0a):
    > read the 11.1.4/11.1.5 notes directly, confirm iMotions 11.1.5 ↔ B-Alert
    > Live 3.1x compatibility once the license activates, and confirm Smart Eye
    > Tracker software ≥ 10.1.2 (iMotions 11.1.0 fixed a calibration bug for
    > older Smart Eye software, which matters for our every-break recalibration).
    > See `INTEGRATION_VERSION_PLAN.md`.

11. **Existing Python packages**: Are there any Python packages already installed on the lab machine for interfacing with these systems (e.g., `pylsl`, `tobii_research`)?
    > **Resolved**: Not needed. Only Python's built-in `socket` module is required for the marker path.

---

### Workflow & Failure Handling (new — for PI)

These questions arose after confirming the live API is viable. They affect study workflow and data quality, not just the implementation.

12. **Who starts and stops the iMotions recording?** Two options:
    - (a) RA clicks "Start" in iMotions, then launches `run_session.py`. Task software only sends markers into an already-running recording.
    - (b) `run_session.py` uses the Remote Control API (port 8087) to start the iMotions study automatically when the participant clicks Continue.
    > **Resolved (May 2026)**: Both paths are built. The Remote Control client is implemented but feature-flagged **off** by default (`IMOTIONS_REMOTE_ENABLED=0`). Production runs use option (a) until the Remote Control wire format is verified on the lab machine — then the flag can be flipped without code changes.
    > **Confirmed by PI (June 2026)**: Option (a) — the RA starts the iMotions recording. Flag stays off.

13. **Per-participant iMotions setup**: Will each participant be a new "respondent" inside one shared iMotions study, or will a new iMotions study be created per session? This determines whether the task script needs to pass a respondent name through the Remote Control API or whether the RA enters it in iMotions before launching the task.
    > **Resolved (June 2026, PI)**: One shared study with a new respondent per participant (recommended model accepted). PI will help set up the study after a handover from James; a joint working call (PI + Jeff, possibly Lina) is being scheduled.

14. **Stimulus event granularity for markers**: For each CVT trial, should the marker stream include:
    - (a) only stimulus onset (and the local JSON has the rest)
    - (b) onset + offset as a paired scene start/end ("range marker")
    - (c) onset, offset, and a separate response marker
    > **Resolved (May 2026)**: Option (c) — most granular. Every trial emits a `scene_start`/`scene_end` pair around the stimulus plus a discrete `response` marker on keypress. Worst-case ~12k markers per session is trivial for TCP localhost; if the iMotions timeline becomes unreadable the emitter can be collapsed to (a) without changing trial code.

15. **Signal vs. non-signal labels in CVT markers**: Should the marker name distinguish trial type (`cvt_signal_onset` vs. `cvt_nonsignal_onset`)? This makes ERP epoching trivial but reveals trial type in the iMotions timeline (acceptable for offline analysis; only matters if anyone observes the recording live).
    > **Resolved (May 2026)**: Distinguish — `CvtMarkerEmitter` emits `cvt_signal_stim` vs `cvt_nonsignal_stim`. Live observation is not part of the study protocol so timeline visibility is acceptable.

16. **Failure tolerance**: If iMotions is not running, or the TCP connection drops mid-block, should the task:
    - (a) abort the block immediately (preserves biosensor coverage but loses behavioral data)
    - (b) continue with a warning logged locally (preserves behavioral data; biosensor alignment may be partially recoverable post-hoc)
    > **Resolved (May 2026)**: Option (b) — implemented as the fail-soft pattern in `EventReceivingAPI` and `RemoteControlAPI`. Any socket error flips `enabled=False`, logs a warning, and the trial loop continues. The behavioral JSON is the primary record.

17. **Timing-precision target**: What alignment precision is required between the task markers and the EEG/eye-tracking streams for the analyses planned (Engagement Index, Frontal Theta, fixation/saccade events)? This sets the threshold for whether the localhost-TCP path (typically sub-ms) is sufficient or whether we should add a redundant hardware trigger.
    > **Resolved (June 2026, PI)**: Sub-millisecond is sufficient — localhost TCP path stands, no hardware trigger.

18. **Recording continuity**: The Remote Control API starts/stops *all sensors at once* — there is no public way to toggle EEG vs. eye-tracking independently. Should the iMotions recording be:
    - (a) one continuous recording for the whole session (EEG + eye-tracking active during practice, breaks, and both tasks), or
    - (b) segmented — start at the beginning of CVT, stop after, restart for PVT?
    > **Resolved (May 2026)**: Option (a) — one continuous recording. `run_session` opens the Event Receiving connection once after the EEG baseline hold and wraps the whole run in a `session_<pid>_<ts>` scene. The inter-task break is bracketed by `session_break_start`/`session_break_end` discrete markers for offline epoching.

19. **Calibration timing in the session**: Eye-tracker calibration (Tobii 9-point) and B-Alert impedance checks happen through iMotions' own UI before recording starts — PsychoPy can't trigger them mid-session. Confirm the intended session order:
    - RA seats participant → RA runs Tobii calibration + B-Alert impedance in iMotions → RA launches `run_session.py` → app sends EEG-baseline hold screen → recording proceeds.
    > Is re-calibration ever needed between blocks (e.g., if the participant shifts position)? If so, the app needs an explicit pause point where the RA can re-enter iMotions.
    > **Resolved (June 2026, PI)**: Session order confirmed (Smarteye calibration, not Tobii). **Yes — every 5-minute break (between the two 24-minute blocks of each task, and between CVT and PVT) requires eye-tracking recalibration.** Implemented as `session_utils.recalibration_hold`: after each timed break the app holds on an RA screen until recalibration is confirmed, bracketed by `recalibration_start`/`recalibration_end` markers.

20. **iMotions study definition ownership**: Using the Remote Control API requires an iMotions study definition (sensor list, recording settings) to already exist by name. Who builds and maintains it? Suggested model: one canonical "Vigilance_CVT_PVT" study, defined once, with a new respondent added per participant. Confirm — and confirm who has admin rights in iMotions to create/edit the study.
    > **Resolved (June 2026, PI)**: PI will help with study setup after getting the handover from James; shared-study/respondent-per-participant model accepted. Joint setup call to be scheduled (Thursday/Friday evening), possibly with Lina.

---

*Prepared by Jeff Roszell — March 2026*
*Updated with iMotions API research findings — April 2026*
*Resolved 6 of 11 questions and added workflow questions for PI — May 2026*
*Phase 2 implementation: resolved Q12, Q14, Q15, Q16, Q18 with PI choices baked into code — May 2026*
*PI answers received (Jeff_questions_U2): resolved Q3, Q6, Q8, Q13, Q17, Q19, Q20; confirmed Q12 option (a); added error-of-omission/commission markers and recalibration holds — June 2026*
*Software versions confirmed (U. Gupta): iMotions 11.1.5, B-Alert Live 3.1x — resolved Q10; version verification folded into the lab E2E plan — June 2026*
