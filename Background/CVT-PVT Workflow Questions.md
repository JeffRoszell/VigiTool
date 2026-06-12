# CVT/PVT — Workflow & Study-Design Questions

Hi Utkarsh,

Before I start building, there are a few workflow and study-design decisions that need your or Dr. Poltavski's input. I've grouped them below; where I have a recommendation I've noted it — feel free to override.

**Questions 3, 8, and 10 are the most blocking** — they'll shape how I sequence the next development phase. No rush on the rest; happy to discuss in person if easier.

---

## Hardware & Software

**1. Smarteye's role.** How is Smarteye being used alongside the Tobii — redundant eye-tracking, head tracking, or something else? Does it route through iMotions, or do we need to handle it separately?

**2. Software versions on the lab machine.** Could you let me know which versions of iMotions, B-Alert Live, Tobii Pro Lab, and Smarteye are installed?

## iMotions Setup

**3. iMotions study definition.** Building the iMotions study (sensor list, recording settings) needs to happen once before any participant runs. Will you or Dr. Poltavski set that up, or should I get iMotions access to build it?

*Recommendation:* one shared study (e.g. `Vigilance_CVT_PVT`) with a new respondent added per participant.

## Event Markers

**4. Confirm the event list.** I plan to mark: block start/end, each 6-minute period transition, stimulus onset, participant response, practice start/end, and the difficulty condition. Should we also mark stimulus offset, or is onset enough?

**5. Stimulus marker granularity (CVT).** For each trial, three options:

- (a) onset only
- (b) onset + offset as a paired range marker
- (c) onset, offset, and a separate response marker

**6. Should marker labels reveal signal vs. non-signal?** (e.g., `cvt_signal_onset` vs. `cvt_nonsignal_onset`.) Makes offline epoching trivial; only matters if someone is watching the iMotions timeline live during recording.

**7. Timing-precision target.** What alignment precision do you need between markers and the EEG / eye-tracking streams for the planned analyses (Engagement Index, Frontal Theta, fixation/saccade events)? Sub-millisecond is achievable on the same machine; if tighter is required I would add a hardware trigger.

## Session Workflow

**8. Who starts the iMotions recording?**

- (a) The RA clicks Start in iMotions, then launches the task software. Task only sends markers.
- (b) The task software triggers iMotions to start recording automatically.

**9. Recording continuity.** iMotions starts/stops all sensors together — there's no public way to toggle EEG and eye-tracking independently. Should we use:

- (a) one continuous recording for the entire session (EEG + eye-tracking through practice, breaks, and both tasks), or
- (b) separate recordings for CVT and PVT?

Option (a) is simpler and preserves a continuous EEG baseline; (b) gives smaller, task-scoped files.

**10. Calibration timing.** I'm assuming this order: RA seats participant → runs Tobii calibration and B-Alert impedance in iMotions → launches the task software → task shows the EEG-baseline hold screen → recording proceeds. Does that match what you've been planning? Is re-calibration ever expected between blocks (e.g., if the participant shifts)?

**11. Failure handling.** If iMotions disconnects mid-block (rare but possible), should the task:

- (a) abort the block
- (b) continue, log a warning, finish the behavioral data

---

Thanks!

Jeff
