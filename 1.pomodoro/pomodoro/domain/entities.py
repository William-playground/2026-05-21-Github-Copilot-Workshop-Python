"""Domain entities and value objects for the Pomodoro app."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


SESSION_TYPE_FOCUS = "focus"
SESSION_TYPE_BREAK = "break"
VALID_SESSION_TYPES = frozenset({SESSION_TYPE_FOCUS, SESSION_TYPE_BREAK})


@dataclass(frozen=True)
class Settings:
    """Pomodoro timer configuration."""

    focus_minutes: int
    short_break_minutes: int
    long_break_minutes: int
    long_break_interval: int

    def __post_init__(self) -> None:
        if self.focus_minutes <= 0:
            raise ValueError("focus_minutes must be positive")
        if self.short_break_minutes <= 0:
            raise ValueError("short_break_minutes must be positive")
        if self.long_break_minutes <= 0:
            raise ValueError("long_break_minutes must be positive")
        if self.long_break_interval <= 0:
            raise ValueError("long_break_interval must be positive")


@dataclass(frozen=True)
class Session:
    """A completed pomodoro session record."""

    session_type: str
    duration_seconds: int
    completed_at: datetime
    id: int | None = None

    def __post_init__(self) -> None:
        if self.session_type not in VALID_SESSION_TYPES:
            raise ValueError(f"invalid session_type: {self.session_type!r}")
        if self.duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative")
