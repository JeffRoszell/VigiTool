"""iMotions API clients — Event Receiving (port 8089) + Remote Control (port 8087).

Stdlib only (socket, threading, queue, logging, time). All network failures
are fail-soft: any error flips ``enabled`` to False, logs a warning, and
prevents further send attempts. Trial-loop code never sees an exception.

Wire format reference: REQUIREMENTS_INTEGRATION.md §5.2, confirmed against
the iMotions Feb 2026 Python reference implementation.
"""
from __future__ import annotations

import logging
import queue
import socket
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Max queued markers before put_nowait raises. Sized for a worst-case 24-min
# high-difficulty CVT block (~960 trials × 3 markers ≈ 2880) plus headroom.
_DEFAULT_QUEUE_MAXSIZE = 8192


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


# ── No-op marker client (default for tests and disabled runs) ─────────────


class NoOpMarkerClient:
    """Drop-in marker client whose methods do nothing.

    Used as the default in task code so callers can omit a client entirely
    and the task simply runs without emitting markers.
    """

    enabled = False

    def connect(self) -> bool:
        return False

    def discrete(self, name: str, description: str = "") -> None:  # noqa: ARG002
        return None

    def scene_start(
        self, name: str, description: str = "", media: str = "I"
    ) -> None:  # noqa: ARG002
        return None

    def scene_end(self, name: str) -> None:  # noqa: ARG002
        return None

    def close(self) -> None:
        return None


# ── Logging marker client (tee) ────────────────────────────────────────────


class LoggingMarkerClient:
    """Wraps a marker client and tees every call to a local log file.

    Useful when iMotions misbehaves on the lab machine: a sidecar log
    captures exactly what the task tried to send, with perf_counter
    timestamps, regardless of whether iMotions actually received it.
    Fail-soft on the file side — a broken log file does not stop marker
    delivery to the wrapped client.
    """

    def __init__(self, inner, log_path) -> None:
        self.inner = inner
        self.log_path = Path(log_path)
        self._fh = None
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = self.log_path.open("a", buffering=1, encoding="utf-8")
            self._fh.write(f"# imotions marker log opened {time.time():.6f}\n")
        except OSError as exc:
            logger.warning("LoggingMarkerClient could not open %s: %s", log_path, exc)
            self._fh = None

    @property
    def enabled(self) -> bool:
        return getattr(self.inner, "enabled", False)

    def _write(self, kind: str, *args) -> None:
        if self._fh is None:
            return
        try:
            ts = time.perf_counter()
            self._fh.write(f"{ts:.6f}\t{kind}\t{args!r}\n")
        except OSError:
            self._fh = None

    def connect(self) -> bool:
        ok = bool(self.inner.connect()) if hasattr(self.inner, "connect") else False
        self._write("connect", ok)
        return ok

    def discrete(self, name: str, description: str = "") -> None:
        self._write("discrete", name, description)
        self.inner.discrete(name, description)

    def scene_start(self, name: str, description: str = "", media: str = "I") -> None:
        self._write("scene_start", name, description, media)
        self.inner.scene_start(name, description, media)

    def scene_end(self, name: str) -> None:
        self._write("scene_end", name)
        self.inner.scene_end(name)

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.write(f"# imotions marker log closed {time.time():.6f}\n")
                self._fh.close()
            except OSError:
                pass
            self._fh = None
        if hasattr(self.inner, "close"):
            self.inner.close()


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
        queue_maxsize: int = _DEFAULT_QUEUE_MAXSIZE,
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
        self._queue: queue.Queue[bytes | None] = queue.Queue(maxsize=queue_maxsize)
        self._thread: threading.Thread | None = None

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
            if self.async_send:
                self._thread = threading.Thread(
                    target=self._sender_loop,
                    name="imotions-sender",
                    daemon=True,
                )
                self._thread.start()
            return True
        except OSError as exc:
            logger.warning(
                "iMotions Event API connect failed (%s:%d): %s",
                self.host, self.port, exc,
            )
            self.enabled = False
            self._sock = None
            return False

    def _send_sync(self, payload: bytes) -> None:
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

    def _sender_loop(self) -> None:
        """Daemon thread: drain the queue and send. Stops on sentinel (None)."""
        while True:
            try:
                item = self._queue.get(timeout=0.25)
            except queue.Empty:
                if self._closed:
                    return
                continue
            if item is None:
                return  # sentinel
            if not self.enabled or self._sock is None:
                continue  # drain remainder silently
            try:
                self._sock.sendall(item)
            except OSError as exc:
                logger.warning("iMotions Event API send failed: %s", exc)
                self.enabled = False
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None

    def _dispatch(self, payload: bytes) -> None:
        if not self.enabled:
            return
        if self.async_send:
            try:
                self._queue.put_nowait(payload)
            except queue.Full:
                logger.warning("iMotions Event API queue full; disabling client")
                self.enabled = False
        else:
            self._send_sync(payload)

    def discrete(self, name: str, description: str = "") -> None:
        self._dispatch(format_discrete(name, description))

    def scene_start(self, name: str, description: str = "", media: str = "I") -> None:
        self._dispatch(format_scene_start(name, description, media))

    def scene_end(self, name: str) -> None:
        self._dispatch(format_scene_end(name))

    def close(self) -> None:
        """Stop the sender thread, drain remaining markers, close the socket."""
        if self._closed:
            return
        self._closed = True
        if self._thread is not None and self._thread.is_alive():
            try:
                self._queue.put_nowait(None)  # sentinel
            except queue.Full:
                pass
            self._thread.join(timeout=1.0)
            self._thread = None
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


# ── Remote Control API wire format ─────────────────────────────────────────
#
# Reference: iMotions Programmer's Guide. Commands follow the same
# semicolon-delimited / CRLF-terminated pattern as the Event Receiving API,
# but the leading message type is 'R' (remote control) rather than 'M'.
#
# Common commands seen in iMotions reference code and third-party wrappers:
#   R;1;;RUN;<StudyName>;<RespondentName>;<Age>;<Gender>;\r\n
#   R;1;;CANCEL;;;;;\r\n
#   R;1;;STATUS;;;;;\r\n
#
# TODO(lab E2E): Verify these bytes against the official Feb 2026
# control_imotions.py reference on the lab machine. If the field count or
# command keywords differ, update only the format_* helpers below — the
# RemoteControlAPI class itself is protocol-agnostic.


def format_run_study(
    study_name: str,
    respondent_name: str,
    age: str = "",
    gender: str = "",
) -> bytes:
    line = (
        "R;1;;RUN;"
        f"{_sanitize(study_name)};"
        f"{_sanitize(respondent_name)};"
        f"{_sanitize(age)};"
        f"{_sanitize(gender)};\r\n"
    )
    return line.encode("utf-8")


def format_cancel_study() -> bytes:
    return b"R;1;;CANCEL;;;;;\r\n"


def format_status_query() -> bytes:
    return b"R;1;;STATUS;;;;;\r\n"


class RemoteControlAPI:
    """Client for the iMotions Remote Control API (default 127.0.0.1:8087).

    Synchronous; commands are infrequent (one start at session begin, one
    stop at session end) and the calling code reasonably waits for them.
    Same fail-soft semantics as EventReceivingAPI — any socket error sets
    enabled=False and silently no-ops subsequent calls.

    Wired into run_session behind a feature flag that defaults to off until
    the wire format is verified against the lab's installed iMotions version.
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
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.send_timeout = send_timeout
        self.enabled = enabled
        self._sock: socket.socket | None = None
        self._connected = False
        self._closed = False

    def connect(self) -> bool:
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
            logger.info(
                "iMotions Remote Control API connected to %s:%d", self.host, self.port
            )
            return True
        except OSError as exc:
            logger.warning(
                "iMotions Remote Control API connect failed (%s:%d): %s",
                self.host, self.port, exc,
            )
            self.enabled = False
            self._sock = None
            return False

    def _send(self, payload: bytes) -> bool:
        if not self.enabled or self._sock is None:
            return False
        try:
            self._sock.sendall(payload)
            return True
        except OSError as exc:
            logger.warning("iMotions Remote Control API send failed: %s", exc)
            self.enabled = False
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
            return False

    def start_study(
        self,
        study_name: str,
        respondent_name: str,
        age: str = "",
        gender: str = "",
    ) -> bool:
        return self._send(format_run_study(study_name, respondent_name, age, gender))

    def stop_study(self) -> bool:
        return self._send(format_cancel_study())

    def status(self) -> bool:
        return self._send(format_status_query())

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
