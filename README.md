# VigiTool

Vigilance task suite for IRB #0007078 — UND Psychology Department.

Compares sustained attention in younger adults (18–35) and older adults (65+) using concurrent EEG and eye-tracking (future phase). Built with [PsychoPy](https://www.psychopy.org/) for millisecond-accurate stimulus timing.

**PI:** Dr. Poltavski · **Co-PI:** Dr. Gupta · **Developer:** Jeff Roszell (BME)

---

## Tasks

### CVT — Cognitive Vigilance Task
Based on Claypoole et al. (2019). Two-digit numbers appear in screen quadrants; press **spacebar** when the difference between digits is 0 or ±1. Two difficulty conditions (high: 500 ms ISI, low: 1500 ms ISI). 24-minute blocks, 4 periods, 20 signals per block. Measures d′, criterion, hit rate, false alarm rate, and vigilance decrement.

### PVT — Psychomotor Vigilance Task
Fixation cross → red circle; press **spacebar** as fast as possible. Two 24-minute sessions (high: 500 ms ISI, low: 1500 ms ISI). Measures mean RT, lapses (RT > 500 ms), and anticipatory responses (RT < 100 ms).

---

## Setup

**Python 3.8 or 3.10 recommended** (per PsychoPy docs). Python 3.9 also works.

```bash
git clone https://github.com/JeffRoszell/VigiTool.git
cd VigiTool
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

**Windows / Linux** — standard install:
```bash
pip install psychopy
```

**macOS** — `tables` (HDF5) fails to build without system headers; install without it:
```bash
pip install --upgrade pip
pip install --no-deps psychopy
pip install six scipy "pyglet==1.5.27" numpy pillow pyopengl wxPython configobj \
    requests json-tricks freetype-py psutil future pyyaml pyzmq ujson soundfile \
    pyserial pandas openpyxl matplotlib imageio imageio-ffmpeg gitpython \
    cryptography beautifulsoup4 astunparse arabic-reshaper python-bidi \
    msgpack msgpack-numpy pyarrow websockets xmlschema zeroconf \
    "questplus>=2023.1" "gevent==25.5.1" "zope.event==5.0" "zope.interface==7.2" \
    "setuptools==78.1.1" "pyobjc>8.0" "pyobjc-core>8.0" \
    "pyobjc-framework-Quartz>8.0" "pyobjc-framework-ScriptingBridge>8.0"
```

## Running the Tasks

```bash
# From the project root (so data/ saves in the right place)
python src/cvt_task.py   # Cognitive Vigilance Task
python src/pvt_task.py   # Psychomotor Vigilance Task  (coming soon)
```

A dialog will appear at launch — enter participant ID, age, difficulty, and optionally tick **Test mode** for a 2-minute run.

---

## Developer Setup

```bash
pip install pytest ruff

# Lint
ruff check src/ tests/

# Test (no PsychoPy required)
pytest tests/ -v
```

---

## Project Structure

```
VigiTool/
├── src/                    # Active PsychoPy implementation (in progress)
├── legacy/                 # Frozen original tkinter code — do not modify
├── tests/                  # pytest test suite
├── data/                   # Participant output (gitignored — IRB requirement)
├── Background/             # Reference papers and IRB documents
├── REQUIREMENTS.md         # Core task requirements
├── REQUIREMENTS_INTEGRATION.md  # EEG/eye-tracking integration (future)
├── MIGRATION_PLAN.md       # tkinter → PsychoPy migration roadmap
├── KNOWN_ISSUES.md         # Documented bugs in legacy code
└── QUESTIONS_FOR_PI.md     # Open protocol questions for Poltavski/Gupta
```

---

## Status

| Component | Status |
|-----------|--------|
| CVT (PsychoPy) | Complete |
| PVT (PsychoPy) | In progress |
| Unified launcher | Planned |
| iMotions integration | Planned (Phase 2) |
| EEG / eye-tracking | Planned (Phase 3) |

---

## Data

Participant data is saved to `data/<participant_id>/` as JSON and is **never committed to version control** per IRB #0007078 data handling requirements.
