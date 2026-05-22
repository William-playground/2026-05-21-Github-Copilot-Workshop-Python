"""Application services (use cases).

These orchestrate Domain + Infrastructure (Repository, Clock) and contain no
HTTP / framework concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from ..domain.entities import (
    SESSION_TYPE_FOCUS,
    VALID_SESSION_TYPES,
    Session,
    Settings,
)
from ..infrastructure.clock import Clock
from ..infrastructure.repositories import SessionRepository, SettingsRepository


class ValidationError(ValueError):
    """Raised when input fails domain/application validation."""


@dataclass(frozen=True)
class TodayStats:
    completed_count: int
    focus_seconds_total: int


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def record_session(
    repo: SessionRepository,
    *,
    session_type: str,
    duration_seconds: int,
    completed_at: datetime,
) -> Session:
    """Persist a completed session after validation."""
    if session_type not in VALID_SESSION_TYPES:
        raise ValidationError(f"invalid session_type: {session_type!r}")
    if not isinstance(duration_seconds, int) or isinstance(duration_seconds, bool):
        raise ValidationError("duration_seconds must be an integer")
    if duration_seconds < 0:
        raise ValidationError("duration_seconds must be non-negative")
    if not isinstance(completed_at, datetime):
        raise ValidationError("completed_at must be a datetime")
    session = Session(
        session_type=session_type,
        duration_seconds=duration_seconds,
        completed_at=_to_utc(completed_at),
    )
    return repo.add(session)


def get_today_stats(repo: SessionRepository, clock: Clock) -> TodayStats:
    """Aggregate today's completed focus sessions using the given Clock.

    "Today" means the UTC calendar date returned by `clock.now()`. Only focus
    sessions count toward `completed_count` and `focus_seconds_total`.
    """
    today = _to_utc(clock.now()).date()
    sessions = repo.list_for_date(today)
    focus_sessions = [s for s in sessions if s.session_type == SESSION_TYPE_FOCUS]
    return TodayStats(
        completed_count=len(focus_sessions),
        focus_seconds_total=sum(s.duration_seconds for s in focus_sessions),
    )


def get_settings(repo: SettingsRepository) -> Settings:
    return repo.get()


def update_settings(
    repo: SettingsRepository,
    *,
    focus_minutes: int,
    short_break_minutes: int,
    long_break_minutes: int,
    long_break_interval: int,
) -> Settings:
    for name, value in (
        ("focus_minutes", focus_minutes),
        ("short_break_minutes", short_break_minutes),
        ("long_break_minutes", long_break_minutes),
        ("long_break_interval", long_break_interval),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValidationError(f"{name} must be an integer")
        if value <= 0:
            raise ValidationError(f"{name} must be positive")
    settings = Settings(
        focus_minutes=focus_minutes,
        short_break_minutes=short_break_minutes,
        long_break_minutes=long_break_minutes,
        long_break_interval=long_break_interval,
    )
    return repo.update(settings)
