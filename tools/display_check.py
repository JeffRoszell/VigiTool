"""Bench check for the task display modes. No participant, no data collected.

Run from the repository root on the lab machine, with the second monitor
attached and iMotions open on it:

    python tools/display_check.py

For each mode in turn (Fullscreen, Borderless, Borderless with no trim) it:

1. opens the task window on the chosen display exactly as the tasks do,
2. compares the window's size and position with the screen's,
3. records frame intervals for CAPTURE_SECONDS while a bar moves across the
   screen — try capturing it with iMotions screen recording or the Snipping
   Tool during this time, and
4. writes everything to data/_display_check/display_check_<timestamp>.txt.

Frame intervals are software flip times. They show dropped frames and jitter,
not the true photon latency; that needs a photodiode.

Press SPACE to skip to the next mode, ESC to stop.
"""
from __future__ import annotations

import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import session_utils  # noqa: E402
from session_utils import (  # noqa: E402
    borderless_size,
    display_problems,
    make_window,
    measure_refresh_hz,
    resolve_screen_index,
    screen_count,
    screen_geometry,
    window_geometry,
)

CAPTURE_SECONDS = 20.0
VARIANTS = (
    ("Fullscreen", "fullscreen", session_utils.BORDERLESS_TRIM_PX),
    ("Borderless (1 px trim)", "borderless", session_utils.BORDERLESS_TRIM_PX),
    ("Borderless (no trim)", "borderless", 0),
)


def frame_stats(intervals_s: list[float]) -> dict:
    """Summarise frame intervals. A frame counts as dropped above 1.5x the median."""
    if len(intervals_s) < 2:
        return {"frames": len(intervals_s)}
    ms = [i * 1000.0 for i in intervals_s]
    median = statistics.median(ms)
    return {
        "frames": len(ms),
        "mean_ms": round(statistics.mean(ms), 3),
        "median_ms": round(median, 3),
        "sd_ms": round(statistics.stdev(ms), 3),
        "max_ms": round(max(ms), 3),
        "dropped": sum(1 for m in ms if m > 1.5 * median),
    }


def run_variant(screen: int, label: str, mode: str, trim_px: int) -> tuple[list[str], bool]:
    from psychopy import core, event, visual  # noqa: PLC0415

    geometry = screen_geometry(screen)
    lines = [f"== {label} =="]
    if mode == "borderless" and geometry is None:
        return lines + ["  skipped: screen geometry could not be read"], True

    win = make_window(screen=screen, mode=mode, geometry=geometry, trim_px=trim_px)
    stopped = False
    try:
        actual = window_geometry(win)
        problems = display_problems(mode, geometry, actual, trim_px=trim_px)
        refresh = measure_refresh_hz(win)
        lines += [
            f"  screen geometry : {None if geometry is None else geometry._asdict()}",
            f"  window geometry : {None if actual is None else actual._asdict()}",
        ]
        if mode == "borderless" and geometry is not None:
            lines.append(f"  expected size   : {borderless_size(geometry, trim_px)}")
        lines += [
            f"  refresh (Hz)    : {refresh}",
            f"  problems        : {problems or 'none'}",
        ]

        text = visual.TextStim(
            win, text=f"{label}\n\nTry capturing this screen now.\nSPACE = next, ESC = stop",
            height=0.07, color="white", pos=(0, 0.4),
        )
        bar = visual.Rect(win, width=0.05, height=1.0, fillColor="white", lineColor=None)
        win.recordFrameIntervals = True
        clock = core.Clock()
        while clock.getTime() < CAPTURE_SECONDS:
            bar.pos = (((clock.getTime() * 0.5) % 2.0) - 1.0, -0.3)
            bar.draw()
            text.draw()
            win.flip()
            keys = event.getKeys(keyList=["space", "escape"])
            if "escape" in keys:
                stopped = True
                break
            if "space" in keys:
                break
        win.recordFrameIntervals = False
        # The first interval includes the TextStim build; drop it.
        lines.append(f"  frame timing    : {frame_stats(list(win.frameIntervals)[1:])}")
    finally:
        win.close()
    return lines, stopped


def main() -> None:
    from psychopy import core, gui  # noqa: PLC0415

    info = {"Task display": list(range(1, screen_count() + 1)), "Tester initials": ""}
    dlg = gui.DlgFromDict(info, title="Display check", sortKeys=False, copyDict=True)
    if not dlg.OK:
        core.quit()
    result = dlg.dictionary
    screen, fell_back = resolve_screen_index(int(result["Task display"]))

    report = [
        f"Display check {datetime.now().isoformat(timespec='seconds')}",
        f"tester: {result['Tester initials']}",
        f"platform: {sys.platform}",
        f"display chosen: {result['Task display']} (screen index {screen}, fell back: {fell_back})",
        f"screens detected: {screen_count()}",
        "",
    ]
    for label, mode, trim in VARIANTS:
        lines, stopped = run_variant(screen, label, mode, trim)
        report += lines + [
            "  captured by iMotions? ____   captured by Snipping Tool? ____", "",
        ]
        if stopped:
            report.append("stopped by ESC")
            break

    out_dir = Path("data") / "_display_check"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"display_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    out.write_text("\n".join(report) + "\n")
    print("\n".join(report))  # noqa: T201 — the report is this script's output
    print(f"Saved to {out}")  # noqa: T201
    core.quit()


if __name__ == "__main__":
    main()
