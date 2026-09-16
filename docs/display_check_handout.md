# Display Check (about 10 minutes)

## Why

iMotions can't record the task screen while the task runs full screen. The
update adds a **Borderless** mode that should look the same to the participant
but still be capturable. This check tells us whether it works on the lab
laptop, and whether it changes frame timing.

**No participant needed. No task data is collected.**

If anything freezes: **Ctrl + Alt + Delete** → **Task Manager** → **Python** →
**End task**.

## Before you start

- [ ] Pull the latest code (branch `feat/borderless-display`)
- [ ] Second monitor plugged in, Windows set to **Extend these displays**
- [ ] iMotions open on the **second monitor**, with screen recording ready
- [ ] Note the laptop's display settings: **Settings → System → Display**

| | Laptop screen | Second monitor |
|---|---|---|
| Resolution | | |
| Scale (%) | | |
| Main display? | | |

- [ ] **Device Manager → Display adapters** — list every adapter shown:
  ______________________________________

## Run the check

1. From the task folder, run `python tools/display_check.py`.
2. Pick the **Task display** number for the **laptop** screen, and enter your initials.
3. The script shows three versions, one after another, each for 20 seconds:
   **Fullscreen**, **Borderless (1 px trim)**, **Borderless (no trim)**.
   A white bar moves across the screen in each.
4. During each version, **start an iMotions screen recording** (or use the
   Snipping Tool with a delay) and check whether the moving bar is captured.
   Press **SPACE** to move on early, **ESC** to stop.

| Version | iMotions captured it? | Snipping Tool captured it? | Anything odd (thin line at an edge, cursor visible, flicker)? |
|---|---|---|---|
| Fullscreen | ☐ Yes ☐ No | ☐ Yes ☐ No | |
| Borderless (1 px trim) | ☐ Yes ☐ No | ☐ Yes ☐ No | |
| Borderless (no trim) | ☐ Yes ☐ No | ☐ Yes ☐ No | |

## Send back

- This page (photo is fine)
- The report file the script saves: `data/_display_check/display_check_<date>.txt`
  (it is not participant data)

## Until we confirm

Keep running real sessions in **Fullscreen**, the same way as before. Don't
switch real participants to Borderless yet.
