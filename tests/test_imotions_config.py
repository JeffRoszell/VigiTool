"""Tests for src/imotions_config.py — env var parsing and defaults."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import imotions_config  # noqa: E402


def test_defaults(monkeypatch):
    for var in (
        "IMOTIONS_ENABLED",
        "IMOTIONS_REMOTE_ENABLED",
        "IMOTIONS_HOST",
        "IMOTIONS_EVENT_PORT",
        "IMOTIONS_REMOTE_PORT",
        "IMOTIONS_STUDY_NAME",
        "IMOTIONS_EYE_TRACKER",
    ):
        monkeypatch.delenv(var, raising=False)
    cfg = imotions_config.load()
    assert cfg.event_enabled is True
    assert cfg.remote_enabled is False  # PI default per QUESTIONS_INTEGRATION Q12
    assert cfg.host == "127.0.0.1"
    assert cfg.event_port == 8089
    assert cfg.remote_port == 8087
    assert cfg.study_name == "Vigilance_CVT_PVT"
    assert cfg.eye_tracker == "aurora"  # PsychDept preference June 2026
    assert cfg.eye_tracker_display == "Aurora"


def test_disable_event_via_env(monkeypatch):
    monkeypatch.setenv("IMOTIONS_ENABLED", "0")
    assert imotions_config.load().event_enabled is False
    monkeypatch.setenv("IMOTIONS_ENABLED", "false")
    assert imotions_config.load().event_enabled is False


def test_enable_remote_via_env(monkeypatch):
    monkeypatch.setenv("IMOTIONS_REMOTE_ENABLED", "1")
    assert imotions_config.load().remote_enabled is True
    monkeypatch.setenv("IMOTIONS_REMOTE_ENABLED", "yes")
    assert imotions_config.load().remote_enabled is True


def test_custom_host_and_ports(monkeypatch):
    monkeypatch.setenv("IMOTIONS_HOST", "192.168.1.50")
    monkeypatch.setenv("IMOTIONS_EVENT_PORT", "9089")
    monkeypatch.setenv("IMOTIONS_REMOTE_PORT", "9087")
    cfg = imotions_config.load()
    assert cfg.host == "192.168.1.50"
    assert cfg.event_port == 9089
    assert cfg.remote_port == 9087


def test_invalid_port_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("IMOTIONS_EVENT_PORT", "not_a_number")
    assert imotions_config.load().event_port == 8089


def test_custom_study_name(monkeypatch):
    monkeypatch.setenv("IMOTIONS_STUDY_NAME", "PoltavskiLab_Vigilance_2026")
    assert imotions_config.load().study_name == "PoltavskiLab_Vigilance_2026"


def test_eye_tracker_ai_x(monkeypatch):
    monkeypatch.setenv("IMOTIONS_EYE_TRACKER", "ai_x")
    cfg = imotions_config.load()
    assert cfg.eye_tracker == "ai_x"
    assert cfg.eye_tracker_display == "AI-X"


def test_eye_tracker_accepts_hyphen_and_case(monkeypatch):
    monkeypatch.setenv("IMOTIONS_EYE_TRACKER", "AI-X")
    assert imotions_config.load().eye_tracker == "ai_x"
    monkeypatch.setenv("IMOTIONS_EYE_TRACKER", "Aurora")
    assert imotions_config.load().eye_tracker == "aurora"


def test_eye_tracker_invalid_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("IMOTIONS_EYE_TRACKER", "tobii")
    assert imotions_config.load().eye_tracker == "aurora"
