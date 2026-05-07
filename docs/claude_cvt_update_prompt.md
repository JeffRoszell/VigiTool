# Prompt for Claude: Cognitive Vigilance Task (CVT) Updates

## Background (Context for Claude)
We need to update our `cvt_task.py` implementation in the UND Psychology Department vigilance task suite. The PI has reviewed the protocol and requested several modifications to the stimulus presentation, response windows, practice sessions, and general experiment flow based on the latest iteration of the IRB protocol/design ("Cognitive Vigilance Task_U3.docx"). 

The codebase is located in `src/cvt_task.py` and `src/pvt_task.py`. Please make sure that your changes adhere to our existing standards (see `CLAUDE.md`), specifically keeping it in pure Python using PsychoPy, and maintaining our `data/` logging schema without violating IRB constraints.

## Required Modifications

### 1. Stimulus Presentation & Location (CVT)
*   **Locations:** Instead of just 4 quadrants, add a central stimulus display location. Stimuli should be randomized per trial across these 5 locations to avoid order bias.
*   **Signal Distribution:** 
    *   Each 24-minute block (both high and low difficulty) is conceptually broken into four 6-minute periods.
    *   For each 6-minute period, there must be exactly **5 critical signals**.
    *   These 5 critical signals must be spatially distributed as: 4 in the center of each quadrant + 1 in the central display.
    *   Total critical signals per block = 20.
*   **Jitter:** Keep the existing positional jitter (±50 pixels) for the stimuli.

### 2. Response Window & ISI (CVT)
*   **Response Allowed:** Participants must be allowed to respond during the *entire* stimulus duration (which includes both the digit presentation time and the subsequent ISI/blank screen).
*   **Fixation Cross:** Add a fixation sign (`+`) in the center of the screen during the ISI.

### 3. Practice Session (CVT)
*   **Structure:** There should be only ONE practice session at the very beginning of the experiment.
*   **Duration:** 2.5 minutes for the low difficulty level, and 2.5 minutes for the high difficulty level.
*   **Content:** Provide on-screen instructions and examples of 3 critical signals before the trials begin.
*   **Feedback:** During the live practice trials, provide explicit visual feedback (clearly mentioned in large fonts) depending on the participant's response.

### 4. Experiment Flow & Metadata (Both Tasks)
*   **Breaks:** Enforce a timed **5-minute break** between the high and low difficulty blocks of the task. Also, enforce a timed 5-minute break if running multiple tasks.
*   **Participant ID:** Ensure Participant ID is collected as a free-text entry (no forced formats like 'P001').
*   **Metadata Logging:** Do NOT prompt for or log additional metadata (like age group, session number, condition assignment, etc.) in the application. This will be handled via a paper-based questionnaire.
*   **Counterbalancing:** Note that task order and difficulty order within a task will be managed manually by RAs. The application must simply allow the experimenter to input the participant ID and manually select the difficulty order to run.
*   **EEG Baselines:** EEG baselines are recorded only at the very beginning of the session. Ensure the task flow accommodates this initial baseline period before the first task begins if necessary.

## Your Task
1.  **Analyze Current Implementation:** Review `src/cvt_task.py` (and `src/pvt_task.py` for general flow/breaks) to identify where stimulus locations, trial generation logic, response collection, and practice routines are currently handled.
2.  **Update Task Logic:** Implement the changes outlined above, paying special attention to the new 6-minute sub-block signal distribution constraint and the new central fixation/location logic.
3.  **Validate Output:** Ensure that the data saved at the end of the task still cleanly parses and that these changes don't break the existing JSON schema (defined in `REQUIREMENTS.md` and expected by `analyze_data.py`). Provide instructions on how to test these specific edge cases using our `e2e-test` agent.
