"""Tests for src/imotions_api.py.

Layer 1 — wire-format unit tests (no sockets, no threads).
Layer 2 — connection lifecycle (mocked socket, sync send).
Layer 3 — async sender round-trip via stdlib socketserver.
Layer 4 (Phase 5/6) — task injection tests, in test_cvt_trials.py /
test_pvt_metrics.py via FakeMarkerClient.
"""
from __future__ import annotations

import socketserver
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from imotions_api import (  # noqa: E402
    EventReceivingAPI,
    RemoteControlAPI,
    format_cancel_study,
    format_discrete,
    format_run_study,
    format_scene_end,
    format_scene_start,
    format_status_query,
)


# ── Layer 1: wire format ───────────────────────────────────────────────────


def test_discrete_format_basic():
    assert format_discrete("stim_onset", "rt=423") == b"M;2;;;stim_onset;rt=423;D;\r\n"


def test_discrete_format_empty_description():
    assert format_discrete("response") == b"M;2;;;response;;D;\r\n"


def test_scene_start_image_default():
    assert format_scene_start("cvt_high_block") == b"M;2;;;cvt_high_block;;N;I\r\n"


def test_scene_start_image_with_description():
    assert (
        format_scene_start("cvt_signal_stim", "trial=42", media="I")
        == b"M;2;;;cvt_signal_stim;trial=42;N;I\r\n"
    )


def test_scene_start_video_format():
    assert format_scene_start("vid", "demo", media="V") == b"M;2;;;vid;demo;N;V\r\n"


def test_scene_end_format():
    assert format_scene_end("cvt_high_block") == b"M;2;;;cvt_high_block;;E;\r\n"


def test_terminator_is_crlf():
    for msg in (
        format_discrete("a"),
        format_scene_start("a"),
        format_scene_end("a"),
    ):
        assert msg.endswith(b"\r\n")


def test_field_count_invariant():
    """All three marker shapes are 8 semicolon-delimited fields → 7 internal
    delimiters between fields, plus the trailing CRLF."""
    for msg in (
        format_discrete("evt", "desc"),
        format_scene_start("evt", "desc", media="I"),
        format_scene_end("evt"),
    ):
        assert msg.count(b";") == 7, msg


def test_semicolon_sanitization_in_name():
    msg = format_discrete("evt;name", "")
    assert b"evt;name" not in msg
    assert b"evt_name" in msg
    assert msg.count(b";") == 7


def test_semicolon_sanitization_in_description():
    msg = format_discrete("evt", "k=v;extra")
    assert msg.count(b";") == 7
    assert b"k=v_extra" in msg


def test_newline_stripping_in_fields():
    msg = format_discrete("evt\n\rbad", "desc\rline\nnew")
    # only the trailing CRLF should remain
    assert msg.endswith(b"\r\n")
    assert b"\r" not in msg[:-2]
    assert b"\n" not in msg[:-2]


def test_utf8_encoding():
    msg = format_discrete("evt", "café")
    assert isinstance(msg, bytes)
    assert "café".encode("utf-8") in msg


# ── Layer 2: lifecycle (mocked socket, synchronous mode) ───────────────────


def test_enabled_false_constructor_creates_no_socket():
    with patch("imotions_api.socket.socket") as mock_sock:
        client = EventReceivingAPI(enabled=False, async_send=False)
        client.connect()
        client.discrete("evt")
        client.scene_start("blk")
        client.scene_end("blk")
        client.close()
        mock_sock.assert_not_called()


def test_connect_failure_disables_client():
    with patch("imotions_api.socket.socket") as mock_sock:
        sock_instance = MagicMock()
        mock_sock.return_value = sock_instance
        sock_instance.connect.side_effect = ConnectionRefusedError
        client = EventReceivingAPI(async_send=False)
        ok = client.connect()
        assert ok is False
        assert client.enabled is False
        # subsequent sends are silent no-ops
        client.discrete("evt")
        client.scene_start("blk")
        client.scene_end("blk")


def test_send_failure_disables_client():
    with patch("imotions_api.socket.socket") as mock_sock:
        sock_instance = MagicMock()
        mock_sock.return_value = sock_instance
        client = EventReceivingAPI(async_send=False)
        assert client.connect() is True
        sock_instance.sendall.side_effect = BrokenPipeError
        client.discrete("evt")  # must not raise
        assert client.enabled is False
        # subsequent calls are no-ops
        client.scene_start("blk")
        client.scene_end("blk")


def test_successful_send_writes_expected_bytes():
    with patch("imotions_api.socket.socket") as mock_sock:
        sock_instance = MagicMock()
        mock_sock.return_value = sock_instance
        client = EventReceivingAPI(async_send=False)
        assert client.connect() is True
        client.discrete("stim_onset", "rt=423")
        sock_instance.sendall.assert_called_once_with(
            b"M;2;;;stim_onset;rt=423;D;\r\n"
        )


def test_close_is_idempotent():
    with patch("imotions_api.socket.socket") as mock_sock:
        sock_instance = MagicMock()
        mock_sock.return_value = sock_instance
        client = EventReceivingAPI(async_send=False)
        client.connect()
        client.close()
        client.close()  # must not raise


def test_context_manager_connects_and_closes():
    with patch("imotions_api.socket.socket") as mock_sock:
        sock_instance = MagicMock()
        mock_sock.return_value = sock_instance
        with EventReceivingAPI(async_send=False) as client:
            client.discrete("inside")
        sock_instance.close.assert_called()


# ── Layer 3: async-send round-trip via real socket ─────────────────────────


class _RecordingHandler(socketserver.BaseRequestHandler):
    """TCP handler that appends all received bytes to a shared list."""

    def handle(self) -> None:
        # cast for type checkers; server is _RecordingServer
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


def _start_recording_server() -> tuple[_RecordingServer, threading.Thread, bytearray]:
    received = bytearray()
    server = _RecordingServer(("127.0.0.1", 0), _RecordingHandler)
    server.received = received  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, received


def _split_markers(raw: bytes) -> list[bytes]:
    """Split a stream of CRLF-terminated markers; empty trailing entry dropped."""
    parts = raw.split(b"\r\n")
    return [p + b"\r\n" for p in parts if p]


def test_async_round_trip_delivers_all_markers():
    server, thread, received = _start_recording_server()
    port = server.server_address[1]
    try:
        client = EventReceivingAPI(host="127.0.0.1", port=port, async_send=True)
        assert client.connect() is True
        for i in range(100):
            client.discrete(f"evt_{i}", f"i={i}")
        client.close()

        # poll until all 100 CRLF-terminated markers have arrived
        for _ in range(200):
            if bytes(received).count(b"\r\n") >= 100:
                break
            time.sleep(0.01)

        markers = _split_markers(bytes(received))
        assert len(markers) == 100
        # ordering preserved
        assert markers[0] == b"M;2;;;evt_0;i=0;D;\r\n"
        assert markers[99] == b"M;2;;;evt_99;i=99;D;\r\n"
    finally:
        server.shutdown()
        server.server_close()


def test_async_send_does_not_block_main_thread():
    """1000 enqueues should complete well under 1 second on any reasonable box."""
    server, thread, received = _start_recording_server()
    port = server.server_address[1]
    try:
        client = EventReceivingAPI(host="127.0.0.1", port=port, async_send=True)
        assert client.connect() is True
        t0 = time.perf_counter()
        for i in range(1000):
            client.discrete("evt", f"i={i}")
        elapsed = time.perf_counter() - t0
        # Generous bound for CI; in practice this completes in <50ms.
        assert elapsed < 1.0, f"main thread blocked for {elapsed:.2f}s"
        client.close()
    finally:
        server.shutdown()
        server.server_close()


def test_async_queue_overflow_disables_client():
    """Tiny queue + no server-side drain: put_nowait will fail; client disables."""
    with patch("imotions_api.socket.socket") as mock_sock:
        sock_instance = MagicMock()
        mock_sock.return_value = sock_instance
        # Make sender thread block forever on sendall so the queue can fill.
        sendall_event = threading.Event()

        def _block(_data: bytes) -> None:
            sendall_event.wait()

        sock_instance.sendall.side_effect = _block
        client = EventReceivingAPI(async_send=True, queue_maxsize=3)
        assert client.connect() is True
        try:
            # 1 item gets popped by the sender (and blocks), 3 fit in queue,
            # any more should trigger the overflow path.
            for _ in range(50):
                client.discrete("evt")
            assert client.enabled is False
        finally:
            sendall_event.set()
            client.close()


# ── Remote Control API: wire format ────────────────────────────────────────


def test_run_study_format():
    assert (
        format_run_study("Vigilance", "P001", "", "")
        == b"R;1;;RUN;Vigilance;P001;;;\r\n"
    )


def test_run_study_format_with_age_and_gender():
    assert (
        format_run_study("Vigilance", "P001", "27", "F")
        == b"R;1;;RUN;Vigilance;P001;27;F;\r\n"
    )


def test_cancel_study_format():
    assert format_cancel_study() == b"R;1;;CANCEL;;;;;\r\n"


def test_status_query_format():
    assert format_status_query() == b"R;1;;STATUS;;;;;\r\n"


def test_run_study_sanitizes_semicolons_in_fields():
    msg = format_run_study("Study;1", "P;01", "", "")
    assert b"Study;1" not in msg
    assert b"Study_1" in msg
    assert b"P_01" in msg


# ── Remote Control API: lifecycle (mocked socket) ──────────────────────────


def test_remote_enabled_false_creates_no_socket():
    with patch("imotions_api.socket.socket") as mock_sock:
        client = RemoteControlAPI(enabled=False)
        client.connect()
        client.start_study("Study", "P01")
        client.stop_study()
        client.close()
        mock_sock.assert_not_called()


def test_remote_connect_failure_disables_client():
    with patch("imotions_api.socket.socket") as mock_sock:
        sock_instance = MagicMock()
        mock_sock.return_value = sock_instance
        sock_instance.connect.side_effect = ConnectionRefusedError
        client = RemoteControlAPI()
        assert client.connect() is False
        assert client.enabled is False
        # subsequent commands no-op and return False
        assert client.start_study("Study", "P01") is False
        assert client.stop_study() is False


def test_remote_start_study_writes_expected_bytes():
    with patch("imotions_api.socket.socket") as mock_sock:
        sock_instance = MagicMock()
        mock_sock.return_value = sock_instance
        client = RemoteControlAPI()
        assert client.connect() is True
        assert client.start_study("Vigilance_CVT_PVT", "P017") is True
        sock_instance.sendall.assert_called_once_with(
            b"R;1;;RUN;Vigilance_CVT_PVT;P017;;;\r\n"
        )


def test_remote_stop_study_writes_expected_bytes():
    with patch("imotions_api.socket.socket") as mock_sock:
        sock_instance = MagicMock()
        mock_sock.return_value = sock_instance
        client = RemoteControlAPI()
        assert client.connect() is True
        assert client.stop_study() is True
        sock_instance.sendall.assert_called_once_with(b"R;1;;CANCEL;;;;;\r\n")


def test_remote_send_failure_disables_client():
    with patch("imotions_api.socket.socket") as mock_sock:
        sock_instance = MagicMock()
        mock_sock.return_value = sock_instance
        client = RemoteControlAPI()
        assert client.connect() is True
        sock_instance.sendall.side_effect = BrokenPipeError
        assert client.start_study("S", "P") is False
        assert client.enabled is False
        # subsequent calls are no-ops
        assert client.stop_study() is False


def test_remote_close_is_idempotent():
    with patch("imotions_api.socket.socket") as mock_sock:
        sock_instance = MagicMock()
        mock_sock.return_value = sock_instance
        client = RemoteControlAPI()
        client.connect()
        client.close()
        client.close()  # must not raise
