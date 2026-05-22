"""Unit tests for the domain entities (validation rules)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pomodoro.domain.entities import Session, Settings


class TestSettingsValidation:
    def test_valid_settings(self) -> None:
        s = Settings(25, 5, 15, 4)
        assert s.focus_minutes == 25

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"focus_minutes": 0},
            {"focus_minutes": -1},
            {"short_break_minutes": 0},
            {"long_break_minutes": -10},
            {"long_break_interval": 0},
        ],
    )
    def test_invalid_settings_raise(self, kwargs: dict) -> None:
        base = {
            "focus_minutes": 25,
            "short_break_minutes": 5,
            "long_break_minutes": 15,
            "long_break_interval": 4,
        }
        base.update(kwargs)
        with pytest.raises(ValueError):
            Settings(**base)


class TestSessionValidation:
    def test_valid_session(self) -> None:
        s = Session(
            session_type="focus",
            duration_seconds=1500,
            completed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert s.session_type == "focus"

    def test_invalid_type(self) -> None:
        with pytest.raises(ValueError):
            Session(
                session_type="nap",
                duration_seconds=100,
                completed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

    def test_negative_duration(self) -> None:
        with pytest.raises(ValueError):
            Session(
                session_type="focus",
                duration_seconds=-1,
                completed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
