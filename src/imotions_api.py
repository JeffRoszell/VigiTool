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


# ── Wire format (Phase 2) ──────────────────────────────────────────────────


def _sanitize(field: str) -> str:
    raise NotImplementedError


def format_discrete(name: str, description: str = "") -> bytes:
    raise NotImplementedError


def format_scene_start(name: str, description: str = "", media: str = "I") -> bytes:
    raise NotImplementedError


def format_scene_end(name: str) -> bytes:
    raise NotImplementedError


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
        raise NotImplementedError

    def connect(self) -> bool:
        raise NotImplementedError

    def discrete(self, name: str, description: str = "") -> None:
        raise NotImplementedError

    def scene_start(self, name: str, description: str = "", media: str = "I") -> None:
        raise NotImplementedError

    def scene_end(self, name: str) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

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
