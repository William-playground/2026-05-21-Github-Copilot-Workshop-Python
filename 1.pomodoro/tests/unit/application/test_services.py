"""Application-layer unit tests using Fake repositories and FixedClock."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pomodoro.application.services import (
    TodayStats,
    ValidationError,
    get_settings,
    get_today_stats,
    record_session,
    update_settings,
)
from pomodoro.domain.entities import Settings
from pomodoro.infrastructure.clock import FixedClock, SystemClock
from pomodoro.infrastructure.repositories_memory import (
    InMemorySessionRepository,
    InMemorySettingsRepository,
)


UTC = timezone.utc


# --------------------------- record_session ---------------------------


class TestRecordSession:
    def test_records_focus_session(self) -> None:
        repo = InMemorySessionRepository()
        s = record_session(
            repo,
            session_type="focus",
            duration_seconds=1500,
            completed_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        assert s.id == 1
        assert repo.list_for_date(datetime(2026, 1, 1, tzinfo=UTC).date()) == [s]

    def test_invalid_type_rejected(self) -> None:
        repo = InMemorySessionRepository()
        with pytest.raises(ValidationError):
            record_session(
                repo,
                session_type="nap",
                duration_seconds=10,
                completed_at=datetime(2026, 1, 1, tzinfo=UTC),
            )

    def test_negative_duration_rejected(self) -> None:
        repo = InMemorySessionRepository()
        with pytest.raises(ValidationError):
            record_session(
                repo,
                session_type="focus",
                duration_seconds=-1,
                completed_at=datetime(2026, 1, 1, tzinfo=UTC),
            )

    def test_non_datetime_rejected(self) -> None:
        repo = InMemorySessionRepository()
        with pytest.raises(ValidationError):
            record_session(
                repo,
                session_type="focus",
                duration_seconds=10,
                completed_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
            )

    def test_naive_datetime_is_treated_as_utc(self) -> None:
        repo = InMemorySessionRepository()
        s = record_session(
            repo,
            session_type="focus",
            duration_seconds=100,
            completed_at=datetime(2026, 1, 1, 12, 0),  # naive
        )
        assert s.completed_at.tzinfo is not None
        assert s.completed_at.utcoffset() == timedelta(0)


# --------------------------- get_today_stats --------------------------


class TestGetTodayStats:
    def test_empty_returns_zeros(self) -> None:
        repo = InMemorySessionRepository()
        clock = FixedClock(datetime(2026, 1, 15, 12, 0, tzinfo=UTC))
        assert get_today_stats(repo, clock) == TodayStats(0, 0)

    def test_only_focus_sessions_are_counted(self) -> None:
        repo = InMemorySessionRepository()
        clock = FixedClock(datetime(2026, 1, 15, 12, 0, tzinfo=UTC))
        record_session(
            repo,
            session_type="focus",
            duration_seconds=1500,
            completed_at=datetime(2026, 1, 15, 9, 0, tzinfo=UTC),
        )
        record_session(
            repo,
            session_type="focus",
            duration_seconds=1500,
            completed_at=datetime(2026, 1, 15, 10, 0, tzinfo=UTC),
        )
        record_session(
            repo,
            session_type="break",
            duration_seconds=300,
            completed_at=datetime(2026, 1, 15, 9, 30, tzinfo=UTC),
        )
        assert get_today_stats(repo, clock) == TodayStats(
            completed_count=2, focus_seconds_total=3000
        )

    def test_yesterdays_sessions_are_excluded(self) -> None:
        repo = InMemorySessionRepository()
        clock = FixedClock(datetime(2026, 1, 15, 0, 0, 1, tzinfo=UTC))
        record_session(
            repo,
            session_type="focus",
            duration_seconds=1500,
            completed_at=datetime(2026, 1, 14, 23, 59, 59, tzinfo=UTC),
        )
        record_session(
            repo,
            session_type="focus",
            duration_seconds=600,
            completed_at=datetime(2026, 1, 15, 0, 0, 0, tzinfo=UTC),
        )
        assert get_today_stats(repo, clock) == TodayStats(1, 600)

    def test_date_boundary_2359_to_0000(self) -> None:
        """Bug-prevention: A session completed at 23:59 must not leak into the
        next calendar day's stats, and a session at 00:00 must be counted on
        the new day.
        """
        repo = InMemorySessionRepository()
        # First day: clock at 23:59:30 — only the 23:59 session counts.
        clock = FixedClock(datetime(2026, 3, 10, 23, 59, 30, tzinfo=UTC))
        record_session(
            repo,
            session_type="focus",
            duration_seconds=1500,
            completed_at=datetime(2026, 3, 10, 23, 59, 0, tzinfo=UTC),
        )
        # Add a session at exactly 00:00 of the next day.
        record_session(
            repo,
            session_type="focus",
            duration_seconds=1500,
            completed_at=datetime(2026, 3, 11, 0, 0, 0, tzinfo=UTC),
        )

        assert get_today_stats(repo, clock) == TodayStats(1, 1500)

        # Advance clock by 1 minute — now we cross the date boundary.
        clock.set(datetime(2026, 3, 11, 0, 0, 30, tzinfo=UTC))
        assert get_today_stats(repo, clock) == TodayStats(1, 1500)


# --------------------------- settings use cases -----------------------


class TestSettingsUseCases:
    def test_get_returns_repository_value(self) -> None:
        repo = InMemorySettingsRepository(Settings(25, 5, 15, 4))
        assert get_settings(repo) == Settings(25, 5, 15, 4)

    def test_update_persists_new_values(self) -> None:
        repo = InMemorySettingsRepository()
        new = update_settings(
            repo,
            focus_minutes=30,
            short_break_minutes=10,
            long_break_minutes=20,
            long_break_interval=5,
        )
        assert new == Settings(30, 10, 20, 5)
        assert repo.get() == new

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"focus_minutes": 0},
            {"focus_minutes": -1},
            {"short_break_minutes": 0},
            {"long_break_minutes": -2},
            {"long_break_interval": 0},
            {"focus_minutes": "25"},
            {"long_break_interval": True},  # bool must not pass int check
        ],
    )
    def test_update_invalid_input_rejected(self, kwargs: dict) -> None:
        base = {
            "focus_minutes": 25,
            "short_break_minutes": 5,
            "long_break_minutes": 15,
            "long_break_interval": 4,
        }
        base.update(kwargs)
        repo = InMemorySettingsRepository()
        with pytest.raises(ValidationError):
            update_settings(repo, **base)  # type: ignore[arg-type]


# --------------------------- clocks ----------------------------------


class TestClocks:
    def test_system_clock_is_timezone_aware_utc(self) -> None:
        now = SystemClock().now()
        assert now.tzinfo is not None
        assert now.utcoffset() == timedelta(0)

    def test_fixed_clock_requires_aware_datetime(self) -> None:
        with pytest.raises(ValueError):
            FixedClock(datetime(2026, 1, 1, 0, 0))

    def test_fixed_clock_returns_set_instant(self) -> None:
        c = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
        assert c.now() == datetime(2026, 1, 1, tzinfo=UTC)
        c.set(datetime(2026, 6, 1, tzinfo=UTC))
        assert c.now() == datetime(2026, 6, 1, tzinfo=UTC)
