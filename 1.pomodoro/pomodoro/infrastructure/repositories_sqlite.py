"""SQLite 実装のリポジトリ。"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timezone

from pomodoro.domain.entities import CompletedSession, Settings, TodayStats


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


class SessionRepository:
    """セッション記録の永続化。"""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, session: CompletedSession) -> int:
        cur = self._conn.execute(
            "INSERT INTO sessions (session_type, duration_seconds, completed_at) "
            "VALUES (?, ?, ?)",
            (session.session_type, session.duration_seconds, _iso(session.completed_at)),
        )
        self._conn.commit()
        return int(cur.lastrowid or 0)

    def today_stats(self, today: date) -> TodayStats:
        start = datetime.combine(today, time.min, tzinfo=timezone.utc).isoformat()
        end = datetime.combine(today, time.max, tzinfo=timezone.utc).isoformat()
        row = self._conn.execute(
            "SELECT "
            "  COUNT(*) FILTER (WHERE session_type = 'focus') AS cnt, "
            "  COALESCE(SUM(duration_seconds) FILTER (WHERE session_type = 'focus'), 0) AS total "
            "FROM sessions "
            "WHERE completed_at BETWEEN ? AND ?",
            (start, end),
        ).fetchone()
        return TodayStats(
            completed_count=int(row["cnt"] or 0),
            focus_seconds_total=int(row["total"] or 0),
        )


class SettingsRepository:
    """設定の永続化（id=1 の単一行運用）。"""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self) -> Settings:
        row = self._conn.execute(
            "SELECT focus_minutes, short_break_minutes, long_break_minutes, long_break_interval "
            "FROM settings WHERE id = 1"
        ).fetchone()
        if row is None:
            # 初期化されていない場合のデフォルト
            return Settings(25, 5, 15, 4)
        return Settings(
            focus_minutes=int(row["focus_minutes"]),
            short_break_minutes=int(row["short_break_minutes"]),
            long_break_minutes=int(row["long_break_minutes"]),
            long_break_interval=int(row["long_break_interval"]),
        )

    def update(self, settings: Settings) -> Settings:
        settings.validate()
        self._conn.execute(
            "UPDATE settings SET "
            "  focus_minutes = ?, "
            "  short_break_minutes = ?, "
            "  long_break_minutes = ?, "
            "  long_break_interval = ? "
            "WHERE id = 1",
            (
                settings.focus_minutes,
                settings.short_break_minutes,
                settings.long_break_minutes,
                settings.long_break_interval,
            ),
        )
        self._conn.commit()
        return self.get()
