"""Tests for src/imotions_api.py.

Layer 1 — wire-format unit tests (no sockets, no threads).
Layer 2 — connection lifecycle (mocked socket, sync send).
Layer 3 (Phase 4) — socketserver integration tests, added later.
Layer 4 (Phase 5/6) — task injection tests, in test_cvt_trials.py /
test_pvt_metrics.py via FakeMarkerClient.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from imotions_api import (  # noqa: E402
    EventReceivingAPI,
    format_discrete,
    format_scene_end,
    format_scene_start,
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
