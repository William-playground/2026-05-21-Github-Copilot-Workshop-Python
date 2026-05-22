"""アプリケーションサービス（ユースケース）。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pomodoro.domain.entities import CompletedSession, Settings, TodayStats
from pomodoro.infrastructure.clock import Clock, SystemClock
from pomodoro.infrastructure.repositories_sqlite import (
    SessionRepository,
    SettingsRepository,
)


class ValidationError(ValueError):
    """入力バリデーション失敗。"""


def _parse_iso(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValidationError("completed_at must be ISO 8601 string")
    try:
        # 'Z' サフィックスにも対応
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValidationError("completed_at must be ISO 8601 string") from None


class SessionService:
    def __init__(self, repo: SessionRepository, clock: Clock | None = None) -> None:
        self._repo = repo
        self._clock = clock or SystemClock()

    def record(self, payload: dict[str, Any]) -> CompletedSession:
        if not isinstance(payload, dict):
            raise ValidationError("payload must be object")
        session_type = payload.get("type")
        duration = payload.get("duration_seconds")
        completed_at_raw = payload.get("completed_at")

        if session_type not in ("focus", "break"):
            raise ValidationError("type must be 'focus' or 'break'")
        if not isinstance(duration, int) or isinstance(duration, bool) or duration < 0:
            raise ValidationError("duration_seconds must be non-negative int")

        completed_at = (
            _parse_iso(completed_at_raw) if completed_at_raw is not None else self._clock.now()
        )
        session = CompletedSession(
            session_type=session_type,
            duration_seconds=duration,
            completed_at=completed_at,
        )
        session.validate()
        self._repo.add(session)
        return session

    def today_stats(self) -> TodayStats:
        return self._repo.today_stats(self._clock.now().date())


class SettingsService:
    def __init__(self, repo: SettingsRepository) -> None:
        self._repo = repo

    def get(self) -> Settings:
        return self._repo.get()

    def update(self, payload: dict[str, Any]) -> Settings:
        if not isinstance(payload, dict):
            raise ValidationError("payload must be object")
        required = (
            "focus_minutes",
            "short_break_minutes",
            "long_break_minutes",
            "long_break_interval",
        )
        for key in required:
            value = payload.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValidationError(f"{key} must be positive int")
        settings = Settings(
            focus_minutes=payload["focus_minutes"],
            short_break_minutes=payload["short_break_minutes"],
            long_break_minutes=payload["long_break_minutes"],
            long_break_interval=payload["long_break_interval"],
        )
        return self._repo.update(settings)
