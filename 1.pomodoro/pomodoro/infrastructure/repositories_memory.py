"""In-memory Fake repository implementations for unit tests."""

from __future__ import annotations

from datetime import date, timezone

from ..domain.entities import Session, Settings


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._sessions: list[Session] = []
        self._next_id = 1

    def add(self, session: Session) -> Session:
        stored = Session(
            id=self._next_id,
            session_type=session.session_type,
            duration_seconds=session.duration_seconds,
            completed_at=session.completed_at,
        )
        self._next_id += 1
        self._sessions.append(stored)
        return stored

    def list_for_date(self, day: date) -> list[Session]:
        result: list[Session] = []
        for s in self._sessions:
            ts = s.completed_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ts_utc = ts.astimezone(timezone.utc)
            if ts_utc.date() == day:
                result.append(s)
        return sorted(result, key=lambda s: s.completed_at)


class InMemorySettingsRepository:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings(
            focus_minutes=25,
            short_break_minutes=5,
            long_break_minutes=15,
            long_break_interval=4,
        )

    def get(self) -> Settings:
        return self._settings

    def update(self, settings: Settings) -> Settings:
        self._settings = settings
        return settings
