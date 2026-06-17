"""iMotions integration configuration.

Lab-tunable knobs via environment variables. Sensible defaults match the
expected production setup (markers enabled, Remote Control disabled until
the wire format is verified on the lab's iMotions install).

Vars:
  IMOTIONS_ENABLED          on/off for marker streaming (default: on)
  IMOTIONS_REMOTE_ENABLED   on/off for Remote Control API (default: off)
  IMOTIONS_HOST             host for both APIs (default: 127.0.0.1)
  IMOTIONS_EVENT_PORT       Event Receiving API port (default: 8089)
  IMOTIONS_REMOTE_PORT      Remote Control API port (default: 8087)
  IMOTIONS_STUDY_NAME       iMotions study name for Remote Control RUN
                            (default: Vigilance_CVT_PVT)
  IMOTIONS_EYE_TRACKER      Smart Eye device id — "aurora" or "ai_x"
                            (default: aurora). Recorded in session
                            metadata and session scene description for
                            downstream traceability; the task software
                            stays device-agnostic (iMotions handles the
                            actual device integration).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

_TRUTHY = ("1", "true", "yes", "on", "y", "t")

EYE_TRACKER_IDS = ("aurora", "ai_x")
EYE_TRACKER_DISPLAY = {"aurora": "Aurora", "ai_x": "AI-X"}


def _bool_env(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in _TRUTHY


def _int_env(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _str_env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return default if v is None else v


def _eye_tracker_env(default: str) -> str:
    v = os.environ.get("IMOTIONS_EYE_TRACKER")
    if v is None:
        return default
    v = v.strip().lower().replace("-", "_")
    return v if v in EYE_TRACKER_IDS else default


@dataclass(frozen=True)
class IMotionsConfig:
    event_enabled: bool
    remote_enabled: bool
    host: str
    event_port: int
    remote_port: int
    study_name: str
    eye_tracker: str

    @property
    def eye_tracker_display(self) -> str:
        return EYE_TRACKER_DISPLAY.get(self.eye_tracker, self.eye_tracker)


def load() -> IMotionsConfig:
    return IMotionsConfig(
        event_enabled=_bool_env("IMOTIONS_ENABLED", True),
        remote_enabled=_bool_env("IMOTIONS_REMOTE_ENABLED", False),
        host=_str_env("IMOTIONS_HOST", "127.0.0.1"),
        event_port=_int_env("IMOTIONS_EVENT_PORT", 8089),
        remote_port=_int_env("IMOTIONS_REMOTE_PORT", 8087),
        study_name=_str_env("IMOTIONS_STUDY_NAME", "Vigilance_CVT_PVT"),
        eye_tracker=_eye_tracker_env("aurora"),
    )
