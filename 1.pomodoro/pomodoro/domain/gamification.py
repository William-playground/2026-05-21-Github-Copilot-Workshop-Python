"""Gamification domain logic (pure functions).

This module implements XP / level calculations, badge definitions,
streak calculation and weekly / monthly aggregation as pure functions
so they can be unit tested independently from Flask, SQLite, or HTTP.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Sequence

# --- XP / Level ------------------------------------------------------------

XP_PER_FOCUS_SESSION = 10
"""1回の集中ポモドーロ完了で獲得するXP。"""

XP_PER_LEVEL = 100
"""1レベルアップに必要なXP。"""


def xp_from_focus_sessions(focus_session_count: int) -> int:
	"""完了した集中セッション数から累積XPを算出する。"""

	if focus_session_count < 0:
		raise ValueError("focus_session_count must be >= 0")
	return focus_session_count * XP_PER_FOCUS_SESSION


def level_from_xp(xp: int) -> int:
	"""累積XPから現在のレベル(1始まり)を返す。"""

	if xp < 0:
		raise ValueError("xp must be >= 0")
	return xp // XP_PER_LEVEL + 1


def xp_progress(xp: int) -> dict[str, int]:
	"""現在のXP状態を返す。

	Returns dict with keys: ``level``, ``xp``, ``xp_into_level``,
	``xp_for_next_level``.
	"""

	if xp < 0:
		raise ValueError("xp must be >= 0")
	level = level_from_xp(xp)
	xp_into_level = xp % XP_PER_LEVEL
	return {
		"level": level,
		"xp": xp,
		"xp_into_level": xp_into_level,
		"xp_for_next_level": XP_PER_LEVEL,
	}


# --- Streak ---------------------------------------------------------------


def _to_local_date(completed_at: str) -> date:
	"""ISO8601文字列から日付部分(ローカル相当)を取り出す。"""

	# Accept ``YYYY-MM-DD`` or full ISO timestamp.
	return datetime.fromisoformat(completed_at).date()


def streak_from_focus_dates(
	completed_at_values: Iterable[str], *, today: date
) -> int:
	"""集中セッションの ``completed_at`` から連続達成日数を算出する。

	今日(または昨日)から遡って、集中セッションが存在する連続日数を返す。
	今日まだセッションが無い場合は昨日基準でストリークを判定する。
	"""

	completed_days: set[date] = {
		_to_local_date(value) for value in completed_at_values
	}
	if not completed_days:
		return 0

	# Start from today if there's a focus session today, otherwise yesterday
	# so that the streak isn't broken until the day fully passes.
	if today in completed_days:
		cursor = today
	else:
		cursor = today - timedelta(days=1)
		if cursor not in completed_days:
			return 0

	streak = 0
	while cursor in completed_days:
		streak += 1
		cursor -= timedelta(days=1)
	return streak


# --- Badges ---------------------------------------------------------------


@dataclass(frozen=True)
class BadgeDefinition:
	"""バッジ定義。"""

	id: str
	name: str
	description: str


BADGE_DEFINITIONS: tuple[BadgeDefinition, ...] = (
	BadgeDefinition(
		id="first_focus",
		name="はじめの一歩",
		description="初めての集中ポモドーロを完了",
	),
	BadgeDefinition(
		id="streak_3",
		name="3日連続",
		description="3日連続で集中ポモドーロを完了",
	),
	BadgeDefinition(
		id="streak_7",
		name="1週間連続",
		description="7日連続で集中ポモドーロを完了",
	),
	BadgeDefinition(
		id="week_10",
		name="今週10回完了",
		description="今週の集中ポモドーロを10回完了",
	),
	BadgeDefinition(
		id="total_50",
		name="50ポモドーロ達成",
		description="累計で50回の集中ポモドーロを完了",
	),
	BadgeDefinition(
		id="total_100",
		name="100ポモドーロ達成",
		description="累計で100回の集中ポモドーロを完了",
	),
)


def evaluate_badges(
	*,
	total_focus_sessions: int,
	streak_days: int,
	focus_sessions_this_week: int,
) -> list[dict[str, str | bool]]:
	"""現在の統計値から各バッジの達成状況を返す。"""

	thresholds = {
		"first_focus": total_focus_sessions >= 1,
		"streak_3": streak_days >= 3,
		"streak_7": streak_days >= 7,
		"week_10": focus_sessions_this_week >= 10,
		"total_50": total_focus_sessions >= 50,
		"total_100": total_focus_sessions >= 100,
	}
	return [
		{
			"id": badge.id,
			"name": badge.name,
			"description": badge.description,
			"earned": bool(thresholds.get(badge.id, False)),
		}
		for badge in BADGE_DEFINITIONS
	]


# --- Aggregation for charts ----------------------------------------------


@dataclass(frozen=True)
class SessionRecord:
	"""集計用の最小セッション情報。"""

	session_type: str
	duration_seconds: int
	completed_at: str  # ISO8601


def _iter_days(start: date, end: date) -> Iterable[date]:
	cursor = start
	while cursor <= end:
		yield cursor
		cursor += timedelta(days=1)


def aggregate_daily(
	sessions: Sequence[SessionRecord], *, start: date, end: date
) -> list[dict[str, int | str]]:
	"""``start``〜``end`` の各日について、集中セッション数と集中時間(秒)を集計する。"""

	if end < start:
		raise ValueError("end must be >= start")

	counts: Counter[date] = Counter()
	focus_seconds: Counter[date] = Counter()
	for session in sessions:
		if session.session_type != "focus":
			continue
		day = _to_local_date(session.completed_at)
		if start <= day <= end:
			counts[day] += 1
			focus_seconds[day] += max(0, session.duration_seconds)

	return [
		{
			"date": day.isoformat(),
			"focus_count": counts.get(day, 0),
			"focus_seconds": focus_seconds.get(day, 0),
		}
		for day in _iter_days(start, end)
	]


def week_range(today: date) -> tuple[date, date]:
	"""今週の月曜日〜日曜日の期間を返す。"""

	start = today - timedelta(days=today.weekday())
	return start, start + timedelta(days=6)


def month_range(today: date) -> tuple[date, date]:
	"""今月の1日〜末日の期間を返す。"""

	start = today.replace(day=1)
	# Move to next month, then back one day for last day of month
	if start.month == 12:
		next_month = start.replace(year=start.year + 1, month=1)
	else:
		next_month = start.replace(month=start.month + 1)
	end = next_month - timedelta(days=1)
	return start, end


def success_rate(focus_count: int, attempt_count: int) -> float:
	"""完了率(0.0〜1.0)を返す。``attempt_count`` が0の場合は0.0を返す。"""

	if attempt_count <= 0:
		return 0.0
	return min(1.0, focus_count / attempt_count)
