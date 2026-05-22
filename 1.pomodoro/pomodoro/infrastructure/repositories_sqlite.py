"""SQLite-backed repository implementations.

These wrap a `sqlite3.Connection` provided by the Flask app context (`get_db()`).
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone

from ..domain.entities import Session, Settings


def _parse_completed_at(raw: str) -> datetime:
    # SQLite stores ISO 8601; ensure timezone-aware UTC.
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_completed_at(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


class SqliteSessionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, session: Session) -> Session:
        cur = self._conn.execute(
            "INSERT INTO sessions (session_type, duration_seconds, completed_at)"
            " VALUES (?, ?, ?)",
            (
                session.session_type,
                session.duration_seconds,
                _format_completed_at(session.completed_at),
            ),
        )
        self._conn.commit()
        return Session(
            id=int(cur.lastrowid) if cur.lastrowid is not None else None,
            session_type=session.session_type,
            duration_seconds=session.duration_seconds,
            completed_at=session.completed_at,
        )

    def list_for_date(self, day: date) -> list[Session]:
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        next_day = start + timedelta(days=1)
        rows = self._conn.execute(
            "SELECT id, session_type, duration_seconds, completed_at FROM sessions"
            " WHERE completed_at >= ? AND completed_at < ?"
            " ORDER BY completed_at",
            (_format_completed_at(start), _format_completed_at(next_day)),
        ).fetchall()
        return [
            Session(
                id=int(r["id"]),
                session_type=str(r["session_type"]),
                duration_seconds=int(r["duration_seconds"]),
                completed_at=_parse_completed_at(str(r["completed_at"])),
            )
            for r in rows
        ]


class SqliteSettingsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self) -> Settings:
        row = self._conn.execute(
            "SELECT focus_minutes, short_break_minutes, long_break_minutes,"
            " long_break_interval FROM settings WHERE id = 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("settings row missing; DB not initialized")
        return Settings(
            focus_minutes=int(row["focus_minutes"]),
            short_break_minutes=int(row["short_break_minutes"]),
            long_break_minutes=int(row["long_break_minutes"]),
            long_break_interval=int(row["long_break_interval"]),
        )

    def update(self, settings: Settings) -> Settings:
        self._conn.execute(
            "UPDATE settings SET focus_minutes = ?, short_break_minutes = ?,"
            " long_break_minutes = ?, long_break_interval = ? WHERE id = 1",
            (
                settings.focus_minutes,
                settings.short_break_minutes,
                settings.long_break_minutes,
                settings.long_break_interval,
            ),
        )
        self._conn.commit()
        return settings
