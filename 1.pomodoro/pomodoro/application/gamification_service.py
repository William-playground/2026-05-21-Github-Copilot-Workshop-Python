"""Application service that turns persisted sessions into gamification data."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Iterable

from ..domain.gamification import (
	SessionRecord,
	aggregate_daily,
	evaluate_badges,
	month_range,
	streak_from_focus_dates,
	success_rate,
	week_range,
	xp_from_focus_sessions,
	xp_progress,
)


def _today(now: datetime | None = None) -> date:
	return (now or datetime.now()).date()


def _fetch_focus_completed_dates(db: sqlite3.Connection) -> list[str]:
	rows = db.execute(
		"SELECT completed_at FROM sessions "
		"WHERE session_type = 'focus' AND status = 'completed'"
	).fetchall()
	return [row["completed_at"] for row in rows]


def _fetch_sessions(db: sqlite3.Connection) -> list[SessionRecord]:
	rows = db.execute(
		"SELECT session_type, duration_seconds, completed_at, status FROM sessions"
	).fetchall()
	return [
		SessionRecord(
			session_type=row["session_type"],
			duration_seconds=row["duration_seconds"],
			completed_at=row["completed_at"],
		)
		for row in rows
		if row["status"] == "completed"
	]


def _count_focus_attempts(db: sqlite3.Connection) -> tuple[int, int]:
	row = db.execute(
		"SELECT "
		"  SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed, "
		"  COUNT(*) AS total "
		"FROM sessions WHERE session_type = 'focus'"
	).fetchone()
	completed = int(row["completed"] or 0)
	total = int(row["total"] or 0)
	return completed, total


def build_summary(db: sqlite3.Connection, *, now: datetime | None = None) -> dict:
	"""Summary: XP/level/streak/badges and lifetime totals."""

	today = _today(now)
	focus_dates = _fetch_focus_completed_dates(db)
	completed, total_attempts = _count_focus_attempts(db)
	xp = xp_from_focus_sessions(completed)
	streak = streak_from_focus_dates(focus_dates, today=today)

	week_start, week_end = week_range(today)
	week_focus_count = sum(
		1
		for value in focus_dates
		if week_start <= datetime.fromisoformat(value).date() <= week_end
	)

	badges = evaluate_badges(
		total_focus_sessions=completed,
		streak_days=streak,
		focus_sessions_this_week=week_focus_count,
	)

	return {
		"xp": xp_progress(xp),
		"streak_days": streak,
		"total_focus_sessions": completed,
		"focus_sessions_this_week": week_focus_count,
		"success_rate": success_rate(completed, total_attempts),
		"badges": badges,
	}


def build_stats(
	db: sqlite3.Connection,
	*,
	range_name: str,
	now: datetime | None = None,
) -> dict:
	"""Weekly or monthly statistics aggregated by day."""

	today = _today(now)
	if range_name == "week":
		start, end = week_range(today)
	elif range_name == "month":
		start, end = month_range(today)
	else:
		raise ValueError("range must be 'week' or 'month'")

	sessions = _fetch_sessions(db)
	daily = aggregate_daily(sessions, start=start, end=end)

	focus_count = sum(int(item["focus_count"]) for item in daily)
	focus_seconds = sum(int(item["focus_seconds"]) for item in daily)

	# Success rate within the range: completed focus / total focus attempts
	row = db.execute(
		"SELECT "
		"  SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed, "
		"  COUNT(*) AS total "
		"FROM sessions "
		"WHERE session_type = 'focus' "
		"  AND date(completed_at) BETWEEN ? AND ?",
		(start.isoformat(), end.isoformat()),
	).fetchone()
	completed = int(row["completed"] or 0)
	total = int(row["total"] or 0)

	return {
		"range": range_name,
		"start": start.isoformat(),
		"end": end.isoformat(),
		"daily": daily,
		"totals": {
			"focus_count": focus_count,
			"focus_seconds": focus_seconds,
			"success_rate": success_rate(completed, total),
		},
	}


def record_session(
	db: sqlite3.Connection,
	*,
	session_type: str,
	duration_seconds: int,
	completed_at: str | None = None,
	status: str = "completed",
	now: datetime | None = None,
) -> int:
	"""Persist a session record. Returns the new row id."""

	if session_type not in {"focus", "break"}:
		raise ValueError("session_type must be 'focus' or 'break'")
	if not isinstance(duration_seconds, int) or duration_seconds < 0:
		raise ValueError("duration_seconds must be a non-negative int")
	if status not in {"completed", "aborted"}:
		raise ValueError("status must be 'completed' or 'aborted'")

	if completed_at is None:
		completed_at = (now or datetime.now()).isoformat(timespec="seconds")
	else:
		# Validate the ISO timestamp early to surface 400s, not 500s.
		datetime.fromisoformat(completed_at)

	cursor = db.execute(
		"INSERT INTO sessions (session_type, duration_seconds, completed_at, status) "
		"VALUES (?, ?, ?, ?)",
		(session_type, duration_seconds, completed_at, status),
	)
	db.commit()
	return int(cursor.lastrowid or 0)


__all__: Iterable[str] = (
	"build_summary",
	"build_stats",
	"record_session",
)
