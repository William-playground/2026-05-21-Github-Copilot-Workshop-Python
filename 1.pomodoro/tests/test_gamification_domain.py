"""Tests for gamification domain pure functions."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

from pomodoro.domain.gamification import (  # noqa: E402
	BADGE_DEFINITIONS,
	XP_PER_FOCUS_SESSION,
	XP_PER_LEVEL,
	SessionRecord,
	aggregate_daily,
	evaluate_badges,
	level_from_xp,
	month_range,
	streak_from_focus_dates,
	success_rate,
	week_range,
	xp_from_focus_sessions,
	xp_progress,
)


def test_xp_from_focus_sessions_is_linear() -> None:
	assert xp_from_focus_sessions(0) == 0
	assert xp_from_focus_sessions(3) == 3 * XP_PER_FOCUS_SESSION


def test_xp_from_focus_sessions_rejects_negative() -> None:
	with pytest.raises(ValueError):
		xp_from_focus_sessions(-1)


def test_level_starts_at_one_and_increments_every_hundred() -> None:
	assert level_from_xp(0) == 1
	assert level_from_xp(XP_PER_LEVEL - 1) == 1
	assert level_from_xp(XP_PER_LEVEL) == 2
	assert level_from_xp(XP_PER_LEVEL * 3 + 50) == 4


def test_xp_progress_exposes_into_level_and_next_target() -> None:
	progress = xp_progress(250)
	assert progress["level"] == 3
	assert progress["xp"] == 250
	assert progress["xp_into_level"] == 50
	assert progress["xp_for_next_level"] == XP_PER_LEVEL


def _iso(day: date) -> str:
	return day.isoformat() + "T10:00:00"


def test_streak_counts_consecutive_days_including_today() -> None:
	today = date(2026, 5, 21)
	dates = [_iso(today - timedelta(days=i)) for i in range(3)]
	assert streak_from_focus_dates(dates, today=today) == 3


def test_streak_uses_yesterday_if_today_missing() -> None:
	today = date(2026, 5, 21)
	dates = [_iso(today - timedelta(days=i)) for i in range(1, 4)]
	assert streak_from_focus_dates(dates, today=today) == 3


def test_streak_breaks_with_gap() -> None:
	today = date(2026, 5, 21)
	dates = [_iso(today), _iso(today - timedelta(days=2))]
	assert streak_from_focus_dates(dates, today=today) == 1


def test_streak_zero_when_no_sessions() -> None:
	today = date(2026, 5, 21)
	assert streak_from_focus_dates([], today=today) == 0


def test_streak_zero_when_last_session_too_old() -> None:
	today = date(2026, 5, 21)
	assert streak_from_focus_dates([_iso(today - timedelta(days=5))], today=today) == 0


def test_evaluate_badges_first_focus_earned_after_one_session() -> None:
	badges = {b["id"]: b for b in evaluate_badges(
		total_focus_sessions=1, streak_days=0, focus_sessions_this_week=1
	)}
	assert badges["first_focus"]["earned"] is True
	assert badges["streak_3"]["earned"] is False
	assert badges["week_10"]["earned"] is False


def test_evaluate_badges_all_earned_at_high_thresholds() -> None:
	badges = {b["id"]: b for b in evaluate_badges(
		total_focus_sessions=120, streak_days=8, focus_sessions_this_week=12
	)}
	for badge in BADGE_DEFINITIONS:
		assert badges[badge.id]["earned"] is True, badge.id


def test_aggregate_daily_counts_focus_only_and_fills_zero_days() -> None:
	start = date(2026, 5, 18)
	end = date(2026, 5, 24)
	sessions = [
		SessionRecord("focus", 1500, "2026-05-18T09:00:00"),
		SessionRecord("focus", 1500, "2026-05-18T10:00:00"),
		SessionRecord("break", 300, "2026-05-18T09:30:00"),
		SessionRecord("focus", 1500, "2026-05-20T12:00:00"),
	]
	daily = aggregate_daily(sessions, start=start, end=end)
	assert len(daily) == 7
	by_date = {item["date"]: item for item in daily}
	assert by_date["2026-05-18"]["focus_count"] == 2
	assert by_date["2026-05-18"]["focus_seconds"] == 3000
	assert by_date["2026-05-19"]["focus_count"] == 0
	assert by_date["2026-05-20"]["focus_count"] == 1


def test_week_range_starts_monday() -> None:
	start, end = week_range(date(2026, 5, 21))  # Thursday
	assert start == date(2026, 5, 18)
	assert end == date(2026, 5, 24)


def test_month_range_covers_full_month() -> None:
	start, end = month_range(date(2026, 5, 21))
	assert start == date(2026, 5, 1)
	assert end == date(2026, 5, 31)
	start, end = month_range(date(2026, 12, 15))
	assert start == date(2026, 12, 1)
	assert end == date(2026, 12, 31)


def test_success_rate_handles_zero_attempts() -> None:
	assert success_rate(0, 0) == 0.0
	assert success_rate(3, 4) == pytest.approx(0.75)
	assert success_rate(10, 5) == 1.0
