"""ドメインエンティティと値オブジェクト。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

SessionType = Literal["focus", "break"]


@dataclass(frozen=True)
class Settings:
    """ポモドーロ設定（単一行運用）。"""

    focus_minutes: int
    short_break_minutes: int
    long_break_minutes: int
    long_break_interval: int

    def validate(self) -> None:
        for name, value in (
            ("focus_minutes", self.focus_minutes),
            ("short_break_minutes", self.short_break_minutes),
            ("long_break_minutes", self.long_break_minutes),
            ("long_break_interval", self.long_break_interval),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"{name} must be int")
            if value <= 0:
                raise ValueError(f"{name} must be > 0")


@dataclass(frozen=True)
class CompletedSession:
    """完了したセッションの記録。"""

    session_type: SessionType
    duration_seconds: int
    completed_at: datetime

    def validate(self) -> None:
        if self.session_type not in ("focus", "break"):
            raise ValueError("session_type must be 'focus' or 'break'")
        if not isinstance(self.duration_seconds, int) or isinstance(self.duration_seconds, bool):
            raise ValueError("duration_seconds must be int")
        if self.duration_seconds < 0:
            raise ValueError("duration_seconds must be >= 0")
        if not isinstance(self.completed_at, datetime):
            raise ValueError("completed_at must be datetime")


@dataclass(frozen=True)
class TodayStats:
    """今日の進捗集計結果。"""

    completed_count: int
    focus_seconds_total: int
