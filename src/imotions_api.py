"""iMotions API clients — Event Receiving (port 8089) + Remote Control (port 8087).

Stdlib only (socket, threading, queue, logging, time). All network failures
are fail-soft: any error flips ``enabled`` to False, logs a warning, and
prevents further send attempts. Trial-loop code never sees an exception.

Wire format reference: REQUIREMENTS_INTEGRATION.md §5.2, confirmed against
the iMotions Feb 2026 Python reference implementation.
"""
from __future__ import annotations

import logging  # noqa: F401  (used by client; imported now so test patches resolve)
import socket  # noqa: F401

logger = logging.getLogger(__name__)


# Implementations land in Phases 2 (format), 3 (sync client), 4 (async sender),
# and 7 (RemoteControlAPI). At Phase 1 these are stubs so the test file imports
# cleanly and assertions fail with NotImplementedError.


# ── Wire format ────────────────────────────────────────────────────────────
#
# Marker shapes (semicolon-delimited, CRLF-terminated, 8 fields each):
#   Discrete:     M;2;;;<name>;<description>;D;\r\n
#   Scene start:  M;2;;;<name>;<description>;N;<I|V>\r\n
#   Scene end:    M;2;;;<name>;;E;\r\n
# Field positions: 1=M, 2=API version, 3-4=reserved, 5=name, 6=description,
# 7=type code (D/N/E), 8=media hint (I/V for scene start, empty otherwise).


def _sanitize(field: str) -> str:
    """Strip characters that would corrupt the wire format.

    ';' is the field delimiter — replace with '_'.
    '\\r' and '\\n' would create spurious record terminators — drop them.
    """
    return field.replace(";", "_").replace("\r", "").replace("\n", "")


def format_discrete(name: str, description: str = "") -> bytes:
    line = f"M;2;;;{_sanitize(name)};{_sanitize(description)};D;\r\n"
    return line.encode("utf-8")


def format_scene_start(name: str, description: str = "", media: str = "I") -> bytes:
    if media not in ("I", "V"):
        raise ValueError(f"media must be 'I' or 'V', got {media!r}")
    line = f"M;2;;;{_sanitize(name)};{_sanitize(description)};N;{media}\r\n"
    return line.encode("utf-8")


def format_scene_end(name: str) -> bytes:
    line = f"M;2;;;{_sanitize(name)};;E;\r\n"
    return line.encode("utf-8")


# ── Event Receiving API client (Phases 3-4) ────────────────────────────────


class EventReceivingAPI:
    """Client for the iMotions Event Receiving API.

    Persistent TCP socket to ``host:port`` (default 127.0.0.1:8089). Marker
    sends are queued onto a background daemon thread when ``async_send=True``
    so the trial loop never blocks on the network. ``async_send=False`` runs
    sends synchronously for deterministic unit-testing.

    Any socket error during connect or send sets ``self.enabled = False``;
    further calls become no-ops. ``enabled=False`` at construction skips the
    socket entirely (clean dev/CI path).
    """

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8089,
        connect_timeout: float = 0.5,
        send_timeout: float = 0.05,
        enabled: bool = True,
        async_send: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.send_timeout = send_timeout
        self.enabled = enabled
        self.async_send = async_send
        self._sock: socket.socket | None = None
        self._connected = False
        self._closed = False

    def connect(self) -> bool:
        """Open the TCP socket. Returns True on success, False on failure.

        Failure flips ``enabled`` to False so subsequent sends are no-ops.
        """
        if not self.enabled:
            return False
        if self._connected:
            return True
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.connect_timeout)
            sock.connect((self.host, self.port))
            sock.settimeout(self.send_timeout)
            self._sock = sock
            self._connected = True
            logger.info("iMotions Event API connected to %s:%d", self.host, self.port)
            return True
        except OSError as exc:
            logger.warning(
                "iMotions Event API connect failed (%s:%d): %s",
                self.host, self.port, exc,
            )
            self.enabled = False
            self._sock = None
            return False

    def _send(self, payload: bytes) -> None:
        """Synchronous send. Errors disable the client and are swallowed."""
        if not self.enabled or self._sock is None:
            return
        try:
            self._sock.sendall(payload)
        except OSError as exc:
            logger.warning("iMotions Event API send failed: %s", exc)
            self.enabled = False
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def discrete(self, name: str, description: str = "") -> None:
        if not self.enabled:
            return
        self._send(format_discrete(name, description))

    def scene_start(self, name: str, description: str = "", media: str = "I") -> None:
        if not self.enabled:
            return
        self._send(format_scene_start(name, description, media))

    def scene_end(self, name: str) -> None:
        if not self.enabled:
            return
        self._send(format_scene_end(name))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        self._connected = False

    def __enter__(self) -> "EventReceivingAPI":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


# ── Remote Control API client (Phase 7) ────────────────────────────────────


class RemoteControlAPI:
    """Client for the iMotions Remote Control API (default 127.0.0.1:8087).

    Wired into run_session behind a config flag (default off). Same fail-soft
    semantics as EventReceivingAPI.
    """

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8087,
        connect_timeout: float = 0.5,
        send_timeout: float = 0.5,
        enabled: bool = True,
    ) -> None:
        raise NotImplementedError

    def connect(self) -> bool:
        raise NotImplementedError

    def start_study(self, study_name: str, respondent: str) -> bool:
        raise NotImplementedError

    def stop_study(self) -> bool:
        raise NotImplementedError

    def status(self) -> str | None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
