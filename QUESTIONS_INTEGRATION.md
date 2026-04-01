# Technical Questions — EEG & Eye-Tracking Integration
## Vigilance Task Software Development — IRB #0007078

These questions relate to the planned integration of the vigilance task software with the B-Alert X-24 EEG system, Tobii Pro Fusion eye-tracker, and Smarteye platform. This integration is a separate development phase from the core task software.

---

### System Roles & Protocols

1. **B-Alert X-24**: What marker/event protocol does the B-Alert system expect from external software? (LSL stream, TTL pulse via parallel port, serial port, UDP, etc.)

2. **Tobii Pro Fusion**: Does Tobii Pro Lab software accept external event markers? If so, via what protocol? (LSL, SDK API call, etc.)

3. **Smarteye**: What is Smarteye's role in the study alongside the Tobii? Is it a redundant/complementary eye-tracking system, or does it serve a different purpose (e.g., head tracking)? Does it also need event markers from the task software?

4. **Single computer or multiple?** Will the task software, B-Alert, Tobii, and Smarteye all run on the same machine, or across separate machines on a local network?

5. **Existing synchronization**: Is there already a synchronization method between the B-Alert and Tobii/Smarteye systems, or will the task software be the common time reference?

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

8. **Timing precision requirements**: What temporal precision is needed for markers? (e.g., <1 ms, <5 ms, <10 ms)

### Hardware & Software Environment

9. **Lab computer specs**: What OS and hardware is in Research Room B347D? This affects which marker protocols are feasible (e.g., parallel port TTL requires specific hardware).

10. **Software versions**: What versions of B-Alert Live, Tobii Pro Lab, and Smarteye software are installed?

11. **Existing Python packages**: Are there any Python packages already installed on the lab machine for interfacing with these systems (e.g., `pylsl`, `tobii_research`)?

---

*Prepared by Jeff Roszell — March 2026*
*Separate from core task development — planned future phase*
