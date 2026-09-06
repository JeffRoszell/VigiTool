"""End-to-end marker-pipeline tests — full session shape, no iMotions required.

Uses a stdlib socketserver fake on an ephemeral port as the iMotions
stand-in and drives the REAL EventReceivingAPI + CvtMarkerEmitter /
PvtMarkerEmitter through scripted sessions. Asserts the exact byte
stream a real iMotions would receive.

This complements but does not replace:
  - Layer 3 (test_imotions_api.py): wire transport only, no emitter
  - Layer 4 (test_cvt_trials.py, test_pvt_metrics.py): emitter contract
    only, no real wire transport

These tests would have caught any of:
  - emitter→client wiring drift
  - scene_start without matching scene_end
  - byte-format regressions that mask in mocks but show on the wire
  - async sender drops under realistic load
"""
from __future__ import annotations

import socketserver
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cvt_task import CvtMarkerEmitter  # noqa: E402
from imotions_api import EventReceivingAPI  # noqa: E402
from pvt_task import PvtMarkerEmitter  # noqa: E402


# ── Fake iMotions receiver ────────────────────────────────────────────────


class _RecordingHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        received: bytearray = self.server.received  # type: ignore[attr-defined]
        while True:
            try:
                chunk = self.request.recv(4096)
            except OSError:
                return
            if not chunk:
                return
            received.extend(chunk)


class _RecordingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def _start_server() -> tuple[_RecordingServer, bytearray]:
    received = bytearray()
    server = _RecordingServer(("127.0.0.1", 0), _RecordingHandler)
    server.received = received  # type: ignore[attr-defined]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, received


def _wait_for_markers(received: bytearray, n_expected: int, timeout_s: float = 2.0):
    deadline = time.perf_counter() + timeout_s
    while time.perf_counter() < deadline:
        if bytes(received).count(b"\r\n") >= n_expected:
            return
        time.sleep(0.005)


def _split(raw: bytes) -> list[bytes]:
    return [p + b"\r\n" for p in raw.split(b"\r\n") if p]


# ── CVT block — full marker sequence over the wire ────────────────────────


def test_cvt_block_full_marker_stream():
    """Drive one CVT block through the real client + real socket and
    verify every byte iMotions would have received."""
    server, received = _start_server()
    port = server.server_address[1]
    try:
        client = EventReceivingAPI(host="127.0.0.1", port=port, async_send=True)
        assert client.connect() is True
        em = CvtMarkerEmitter(client)

        # Scripted block: 5 trials, mix of signal/nonsignal, mix of responses.
        # Matches what the cvt_task trial loop is supposed to emit.
        em.block_start("high")
        em.period(1)

        # trial 1 — signal, hit at 250ms
        t1 = {"is_signal": True, "trial_number": 1, "period": 1,
              "outcome": "hit", "reaction_time_ms": 250.0}
        em.stim_onset(t1)
        em.response(t1, 250.0)
        em.stim_offset(t1)
        em.outcome(t1)

        # trial 2 — nonsignal, correct rejection (no response)
        t2 = {"is_signal": False, "trial_number": 2, "period": 1,
              "outcome": "correct_rejection", "reaction_time_ms": None}
        em.stim_onset(t2)
        em.stim_offset(t2)
        em.outcome(t2)

        # trial 3 — signal, miss (error of omission)
        t3 = {"is_signal": True, "trial_number": 3, "period": 1,
              "outcome": "miss", "reaction_time_ms": None}
        em.stim_onset(t3)
        em.stim_offset(t3)
        em.outcome(t3)

        # trial 4 — nonsignal, false alarm at 350ms (error of commission)
        t4 = {"is_signal": False, "trial_number": 4, "period": 1,
              "outcome": "false_alarm", "reaction_time_ms": 350.0}
        em.stim_onset(t4)
        em.response(t4, 350.0)
        em.stim_offset(t4)
        em.outcome(t4)

        # trial 5 — signal, hit at 280ms (period transition before this trial)
        em.period(2)
        t5 = {"is_signal": True, "trial_number": 5, "period": 2,
              "outcome": "hit", "reaction_time_ms": 280.0}
        em.stim_onset(t5)
        em.response(t5, 280.0)
        em.stim_offset(t5)
        em.outcome(t5)

        em.block_end("high")

        # Expected sequence — every trial now ends with an outcome marker
        # (PI decision June 2026: errors labeled omission/commission).
        expected = [
            b"M;2;;;cvt_high_block;;N;I\r\n",
            b"M;2;;;cvt_period_1;;D;\r\n",
            b"M;2;;;cvt_signal_stim;trial=1,period=1;N;I\r\n",
            b"M;2;;;cvt_response;rt=250.0,trial=1,kind=signal;D;\r\n",
            b"M;2;;;cvt_signal_stim;;E;\r\n",
            b"M;2;;;cvt_hit;outcome=hit,trial=1,period=1,rt=250.0;D;\r\n",
            b"M;2;;;cvt_nonsignal_stim;trial=2,period=1;N;I\r\n",
            b"M;2;;;cvt_nonsignal_stim;;E;\r\n",
            b"M;2;;;cvt_correct_rejection;outcome=correct_rejection,trial=2,period=1,rt=none;D;\r\n",
            b"M;2;;;cvt_signal_stim;trial=3,period=1;N;I\r\n",
            b"M;2;;;cvt_signal_stim;;E;\r\n",
            b"M;2;;;cvt_error_omission;outcome=miss,trial=3,period=1,rt=none;D;\r\n",
            b"M;2;;;cvt_nonsignal_stim;trial=4,period=1;N;I\r\n",
            b"M;2;;;cvt_response;rt=350.0,trial=4,kind=nonsignal;D;\r\n",
            b"M;2;;;cvt_nonsignal_stim;;E;\r\n",
            b"M;2;;;cvt_error_commission;outcome=false_alarm,trial=4,period=1,rt=350.0;D;\r\n",
            b"M;2;;;cvt_period_2;;D;\r\n",
            b"M;2;;;cvt_signal_stim;trial=5,period=2;N;I\r\n",
            b"M;2;;;cvt_response;rt=280.0,trial=5,kind=signal;D;\r\n",
            b"M;2;;;cvt_signal_stim;;E;\r\n",
            b"M;2;;;cvt_hit;outcome=hit,trial=5,period=2,rt=280.0;D;\r\n",
            b"M;2;;;cvt_high_block;;E;\r\n",
        ]
        _wait_for_markers(received, len(expected))
        client.close()

        markers = _split(bytes(received))
        assert markers == expected, (
            f"\nExpected {len(expected)} markers, got {len(markers)}\n"
            f"First mismatch at index "
            f"{next((i for i, (a, b) in enumerate(zip(markers, expected)) if a != b), 'N/A')}"
        )
    finally:
        server.shutdown()
        server.server_close()


def test_cvt_practice_then_block_session_shape():
    """Practice (low → high) followed by one block — what run_full_session
    produces in the no-skip-practice path."""
    server, received = _start_server()
    port = server.server_address[1]
    try:
        client = EventReceivingAPI(host="127.0.0.1", port=port, async_send=True)
        assert client.connect() is True
        em = CvtMarkerEmitter(client)

        # Practice: low then high, 1 signal trial each
        em.practice_start("low")
        t = {"is_signal": True, "trial_number": 1, "period": 1}
        em.stim_onset(t)
        em.response(t, 300.0)
        em.stim_offset(t)
        em.practice_end("low")

        em.practice_start("high")
        em.stim_onset(t)
        em.response(t, 290.0)
        em.stim_offset(t)
        em.practice_end("high")

        # One short test-mode block
        em.block_start("high")
        em.period(1)
        em.stim_onset(t)
        em.response(t, 270.0)
        em.stim_offset(t)
        em.block_end("high")

        expected = [
            b"M;2;;;cvt_practice_low;;N;I\r\n",
            b"M;2;;;cvt_signal_stim;trial=1,period=1;N;I\r\n",
            b"M;2;;;cvt_response;rt=300.0,trial=1,kind=signal;D;\r\n",
            b"M;2;;;cvt_signal_stim;;E;\r\n",
            b"M;2;;;cvt_practice_low;;E;\r\n",
            b"M;2;;;cvt_practice_high;;N;I\r\n",
            b"M;2;;;cvt_signal_stim;trial=1,period=1;N;I\r\n",
            b"M;2;;;cvt_response;rt=290.0,trial=1,kind=signal;D;\r\n",
            b"M;2;;;cvt_signal_stim;;E;\r\n",
            b"M;2;;;cvt_practice_high;;E;\r\n",
            b"M;2;;;cvt_high_block;;N;I\r\n",
            b"M;2;;;cvt_period_1;;D;\r\n",
            b"M;2;;;cvt_signal_stim;trial=1,period=1;N;I\r\n",
            b"M;2;;;cvt_response;rt=270.0,trial=1,kind=signal;D;\r\n",
            b"M;2;;;cvt_signal_stim;;E;\r\n",
            b"M;2;;;cvt_high_block;;E;\r\n",
        ]
        _wait_for_markers(received, len(expected))
        client.close()
        assert _split(bytes(received)) == expected
    finally:
        server.shutdown()
        server.server_close()


# ── PVT block — full marker sequence over the wire ────────────────────────


def test_pvt_block_full_marker_stream():
    server, received = _start_server()
    port = server.server_address[1]
    try:
        client = EventReceivingAPI(host="127.0.0.1", port=port, async_send=True)
        assert client.connect() is True
        em = PvtMarkerEmitter(client)

        em.block_start()
        em.period(1)

        # ISI early press
        em.anticipatory()

        # trial 1 — valid response (no error marker)
        em.stim_onset(1, 1)
        em.stim_offset()
        em.response(1, 287.0, "valid")
        em.error_outcome(1, "valid", 287.0)

        # foreperiod early press before trial 2
        em.anticipatory()

        # trial 2 — lapse (error of omission)
        em.stim_onset(2, 1)
        em.stim_offset()
        em.response(2, 612.0, "lapse")
        em.error_outcome(2, "lapse", 612.0)

        # trial 3 — timeout / no response (error of omission)
        em.stim_onset(3, 1)
        em.stim_offset()
        em.response(3, None, "timeout")
        em.error_outcome(3, "timeout", None)

        em.block_end()

        expected = [
            b"M;2;;;pvt_block;;N;I\r\n",
            b"M;2;;;pvt_period_1;;D;\r\n",
            b"M;2;;;pvt_anticipatory;phase=foreperiod;D;\r\n",
            b"M;2;;;pvt_error_commission;type=anticipatory,phase=foreperiod;D;\r\n",
            b"M;2;;;pvt_stim;trial=1,period=1;N;I\r\n",
            b"M;2;;;pvt_stim;;E;\r\n",
            b"M;2;;;pvt_response;rt=287.0,type=valid,trial=1;D;\r\n",
            b"M;2;;;pvt_anticipatory;phase=foreperiod;D;\r\n",
            b"M;2;;;pvt_error_commission;type=anticipatory,phase=foreperiod;D;\r\n",
            b"M;2;;;pvt_stim;trial=2,period=1;N;I\r\n",
            b"M;2;;;pvt_stim;;E;\r\n",
            b"M;2;;;pvt_response;rt=612.0,type=lapse,trial=2;D;\r\n",
            b"M;2;;;pvt_error_omission;type=lapse,rt=612.0,trial=2;D;\r\n",
            b"M;2;;;pvt_stim;trial=3,period=1;N;I\r\n",
            b"M;2;;;pvt_stim;;E;\r\n",
            b"M;2;;;pvt_response;rt=none,type=timeout,trial=3;D;\r\n",
            b"M;2;;;pvt_error_omission;type=timeout,rt=none,trial=3;D;\r\n",
            b"M;2;;;pvt_block;;E;\r\n",
        ]
        _wait_for_markers(received, len(expected))
        client.close()
        assert _split(bytes(received)) == expected
    finally:
        server.shutdown()
        server.server_close()


# ── Session-level wrapping — what run_session produces ─────────────────────


def test_session_wrap_with_break_between_tasks():
    """Mirrors what run_session.run emits at the orchestrator level: a
    session scene wrapping everything, break_start/break_end discretes
    around the inter-task break, then session scene_end."""
    server, received = _start_server()
    port = server.server_address[1]
    try:
        client = EventReceivingAPI(host="127.0.0.1", port=port, async_send=True)
        assert client.connect() is True
        cvt = CvtMarkerEmitter(client)
        pvt = PvtMarkerEmitter(client)

        pid = "PILOT01"
        ts = "20260513_143000"
        session_label = f"session_{pid}_{ts}"

        # Session-level wrap (mirrors run_session.run)
        client.scene_start(session_label, description=f"pid={pid}")

        # CVT block (collapsed: just markers, no trials)
        cvt.block_start("high")
        cvt.block_end("high")

        # Inter-task break
        client.discrete("session_break_start")
        client.discrete("session_break_end")

        # PVT block (collapsed)
        pvt.block_start()
        pvt.block_end()

        client.scene_end(session_label)

        expected = [
            b"M;2;;;session_PILOT01_20260513_143000;pid=PILOT01;N;I\r\n",
            b"M;2;;;cvt_high_block;;N;I\r\n",
            b"M;2;;;cvt_high_block;;E;\r\n",
            b"M;2;;;session_break_start;;D;\r\n",
            b"M;2;;;session_break_end;;D;\r\n",
            b"M;2;;;pvt_block;;N;I\r\n",
            b"M;2;;;pvt_block;;E;\r\n",
            b"M;2;;;session_PILOT01_20260513_143000;;E;\r\n",
        ]
        _wait_for_markers(received, len(expected))
        client.close()
        assert _split(bytes(received)) == expected
    finally:
        server.shutdown()
        server.server_close()


# ── ESC mid-block: emitter pattern in finally must still flush block_end ──


def test_esc_midblock_finally_pattern_emits_block_end():
    """run_full_session wraps block_start/block_end in try/finally. Even
    on simulated escape mid-block, the block_end marker must reach the
    server before the client closes."""
    server, received = _start_server()
    port = server.server_address[1]
    try:
        client = EventReceivingAPI(host="127.0.0.1", port=port, async_send=True)
        assert client.connect() is True
        em = CvtMarkerEmitter(client)

        em.block_start("high")
        try:
            em.period(1)
            t = {"is_signal": True, "trial_number": 1, "period": 1}
            em.stim_onset(t)
            # simulate ESC right here — no stim_offset, no response
        finally:
            em.block_end("high")

        expected = [
            b"M;2;;;cvt_high_block;;N;I\r\n",
            b"M;2;;;cvt_period_1;;D;\r\n",
            b"M;2;;;cvt_signal_stim;trial=1,period=1;N;I\r\n",
            b"M;2;;;cvt_high_block;;E;\r\n",
        ]
        _wait_for_markers(received, len(expected))
        client.close()
        assert _split(bytes(received)) == expected
    finally:
        server.shutdown()
        server.server_close()
