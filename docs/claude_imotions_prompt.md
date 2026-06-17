# iMotions API Integration Build Plan & Prompt

**Context:**
We need to integrate iMotions into our PsychoPy vigilance task suite (CVT & PVT) for IRB #0007078. iMotions acts as the central synchronization hub for *both* the EEG (B-Alert X-24) and Eye-Tracking (Tobii Pro Fusion) systems. We do not interface with the EEG or Eye-Tracker SDKs directly; we only talk to iMotions.

**Objective:**
Build an API connection based on the newest iMotions spec (Feb 2026 reference implementation). We need to automatically start/stop the iMotions recording (which controls both EEG and Eye-Tracking) and send precise event markers during the task to ensure perfect timing synchronization. 

Please execute the following build plan in a new feature branch:

### Step 1: Branching
1. Create and checkout a new branch named `feature/imotions-integration`. We will test everything here before merging into the main branch.

### Step 2: Build the iMotions API Module
1. Create a new file `src/imotions_api.py`.
2. Implement two classes using standard Python `socket` (TCP, localhost, UTF-8 encoding):
   - **`RemoteControlAPI` (Port 8087):** To start and stop the iMotions study. 
   - **`EventReceivingAPI` (Port 8089):** To send synchronized event markers.
3. The Event Marker format must strictly follow the Feb 2026 spec:
   - Semicolon-delimited, terminated by `\r\n`
   - Discrete Marker: `M;2;;;<name>;<description>;D;\r\n`
   - Scene Start: `M;2;;;<name>;<description>;N;I\r\n` (for images) or `V` (for videos)
   - Scene End: `M;2;;;<name>;;E;\r\n`

### Step 3: Task Integration (CVT & PVT)
Update `src/cvt_task.py` (and `src/pvt_task.py` if ready) to utilize the new API module:
1. **Session Start/Stop:** Use the `RemoteControlAPI` to start the iMotions recording right after the participant info dialog is submitted, and stop the recording when the task concludes or is aborted (e.g., via ESC key).
2. **Event Markers:** Use the `EventReceivingAPI` to send markers for:
   - Block start / block end (using Scene Start `N` and Scene End `E` pairs)
   - Stimulus onset and offset
   - Participant responses (Discrete `D` markers with timestamp/RT in the description)
   - Practice start / practice end
3. **Failure Handling:** Wrap socket calls in `try/except` blocks. If iMotions isn't running or the connection fails, the task *must* log a warning but continue running normally to preserve behavioral data.

### Step 4: Verification
1. Ensure no external dependencies beyond `socket` were introduced for this connection.
2. Verify that the task does not crash if it cannot connect to `127.0.0.1:8089` or `8087`.

Please provide the code for `src/imotions_api.py` and the necessary updates to `src/cvt_task.py` to achieve this.
