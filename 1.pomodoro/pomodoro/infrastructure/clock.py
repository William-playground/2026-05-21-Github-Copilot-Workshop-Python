"""Clock 抽象化（テスト容易性のため）。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:  # pragma: no cover - Protocol
        ...


class SystemClock:
    """実時刻を返すデフォルトの Clock。"""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock:
    """テスト用に固定時刻を返す Clock。"""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed
