# Technical Questions — EEG & Eye-Tracking Integration
## Vigilance Task Software Development — IRB #0007078

These questions relate to the planned integration of the vigilance task software with the B-Alert X-24 EEG system, Tobii Pro Fusion eye-tracker, and Smarteye platform. This integration is a separate development phase from the core task software.

> **Research note (April 2026)**: iMotions serves as the integration hub — all biosensors sync through it. The task software sends TCP markers to iMotions on port 8089; iMotions handles synchronization with B-Alert, Tobii, and Smarteye internally. This simplifies questions 1–5 considerably. See `REQUIREMENTS_INTEGRATION.md §5` for full API research findings.

---

### System Roles & Protocols

1. **B-Alert X-24**: What marker/event protocol does the B-Alert system expect from external software? (LSL stream, TTL pulse via parallel port, serial port, UDP, etc.)
   > *Partially answered*: B-Alert syncs through iMotions — task software does not communicate with B-Alert directly. iMotions handles the B-Alert data stream internally.

2. **Tobii Pro Fusion**: Does Tobii Pro Lab software accept external event markers? If so, via what protocol? (LSL, SDK API call, etc.)
   > *Partially answered*: Same as above — Tobii syncs through iMotions. Direct Tobii SDK integration is not required.

3. **Smarteye**: What is Smarteye's role in the study alongside the Tobii? Is it a redundant/complementary eye-tracking system, or does it serve a different purpose (e.g., head tracking)? Does it also need event markers from the task software?
   > *Still open*: Role TBD. Confirm with PI whether Smarteye connects to iMotions or needs separate handling.

4. **Single computer or multiple?** Will the task software, B-Alert, Tobii, and Smarteye all run on the same machine, or across separate machines on a local network?
   > *Partially answered*: iMotions and the task software should run on the same machine (TCP to `localhost:8089`). Confirm whether biosensor software also runs locally or on separate acquisition units.

5. **Existing synchronization**: Is there already a synchronization method between the B-Alert and Tobii/Smarteye systems, or will the task software be the common time reference?
   > *Partially answered*: iMotions is the synchronization hub. The task software sends markers; iMotions aligns all streams to those markers.

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
   > *Partially answered*: iMotions API uses string labels in a semicolon-delimited format (e.g., `M;2;;;stimulus_onset;;S;I\r\n`). Exact field definitions require the iMotions Programming Guide PDF from the lab machine — full docs are behind login at `my.imotions.com`.

8. **Timing precision requirements**: What temporal precision is needed for markers? (e.g., <1 ms, <5 ms, <10 ms)
   > *Still open*: Confirm with PI. TCP marker delivery over localhost is typically <1 ms, which should satisfy EEG/eye-tracking alignment needs.

### Hardware & Software Environment

9. **Lab computer specs**: What OS and hardware is in Research Room B347D? This affects which marker protocols are feasible (e.g., parallel port TTL requires specific hardware).
   > *Still open*: TCP over localhost has no special hardware requirements, so this is lower priority now.

10. **Software versions**: What versions of B-Alert Live, Tobii Pro Lab, and Smarteye software are installed?
    > *Still open* — and now add: **What version of iMotions is installed?** The marker format may differ between versions (confirmed format is from iMotions 7.0; current version may differ).

11. **Existing Python packages**: Are there any Python packages already installed on the lab machine for interfacing with these systems (e.g., `pylsl`, `tobii_research`)?
    > *Still open*: With the iMotions TCP approach, `pylsl` and `tobii_research` are not needed. Only Python's built-in `socket` module is required.

---

*Prepared by Jeff Roszell — March 2026*
*Updated with iMotions API research findings — April 2026*
