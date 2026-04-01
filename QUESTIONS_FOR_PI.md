# Technical Questions for Dr. Poltavski & Dr. Gupta
## Vigilance Task Software Development — IRB #0007078

These questions arose during the software requirements phase and need clarification before implementation can begin. They are organized by task.

---

## Psychomotor Vigilance Task (PVT)

### Timing & Structure
1. **Foreperiod range**: What is the range of the random foreperiod (time from fixation cross onset to red circle appearance)? Traditional PVTs use 2–10 seconds. Should we use that range, or something different?

2. **What does the ISI represent in the PVT?** For the CVT, the ISI (500 ms or 1500 ms) is the blank screen between stimulus offset and the next stimulus onset. For the PVT, is the ISI the blank interval between the participant's response and the next fixation cross appearing? Or between the response and the next red circle?

3. **Timeout**: If a participant never responds to the red circle, how long should it remain on screen before we record it as a lapse and move on? (Common values are 10–30 seconds.)

### Stimulus Details
4. **Red circle specifications**: What size should the red circle be (approximate diameter or visual angle)? Filled or outline? Any specific shade of red?

5. **Fixation cross**: Should the fixation cross remain on screen continuously during the foreperiod, or is there a blank interval between the cross and the red circle?

6. **Does the red circle replace the fixation cross, or appear alongside it?**

### Feedback
7. **Should the participant see their reaction time (in ms) after each response?** The traditional PVT shows a millisecond counter, but the IRB describes a simpler red-circle paradigm. Should we show RT feedback, and if so, for how long?

---

## Cognitive Vigilance Task (CVT)

### Stimulus Presentation
8. **Quadrant assignment**: Stimuli appear in four screen quadrants. Are they assigned to quadrants in a fixed rotation (cycling through all four), randomized per trial, or some other pattern?

9. **Positional jitter**: The legacy code adds ±50 pixels of random offset within each quadrant. Should we keep this, adjust it, or remove it?

### Response Window
10. **Can participants respond during the ISI (blank screen)?** The legacy code allows responses during the stimulus display only. Should a response during the blank screen count as a valid response for the preceding stimulus? Claypoole mentions responses are allowed during "the stimulus duration (i.e., either 1,500 ms or 2,500 ms)" — which includes the ISI.

### Practice
11. **Practice task duration**: Claypoole mentions a 5-minute practice period. Should the practice use the same difficulty level (ISI) as the upcoming block, or always use a fixed difficulty?

12. **Practice instructions**: Should the practice include on-screen examples of critical vs. non-critical signals before trials begin, or just written instructions followed by live practice trials?

---

## Both Tasks — General

### Counterbalancing
13. **Task order**: CVT and PVT are counterbalanced across participants. Is there a specific scheme (e.g., alternating by participant number), or is this managed manually?

14. **Difficulty order within a task**: When a participant does both high and low difficulty blocks, is the order also counterbalanced? If so, how — separate from task order or as part of a combined scheme?

### Breaks
15. **Between difficulty blocks**: Is there a required minimum break duration between the high and low difficulty blocks of the same task, or is it experimenter-paced?

16. **Between tasks**: Is there a required break between completing one task (e.g., CVT) and starting the other (e.g., PVT)? The IRB mentions EEG baselines — do those happen before each task or only once at the start?

### Data
17. **Participant ID format**: Is there a preferred format (e.g., P001, YA01/OA01 for younger/older adults), or free-text entry?

18. **Additional metadata to log**: Beyond participant ID and age, should we collect anything else at startup (e.g., age group, session number, experimenter initials, condition assignment)?

---

*Prepared by Jeff Roszell — March 2026*
*For software development of the CVT/PVT vigilance task suite*
