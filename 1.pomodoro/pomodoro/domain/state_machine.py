"""Pomodoro state machine.

Pure-function transition rules. No side effects, no I/O.

States:
    - ``idle``
    - ``running_focus``, ``paused_focus``
    - ``running_short_break``, ``paused_short_break``
    - ``running_long_break``, ``paused_long_break``

Events:
    - ``START``
    - ``PAUSE``
    - ``RESUME``
    - ``RESET``
    - ``COMPLETE_SESSION``

The single entry point is :func:`transition`, which returns a new
:class:`State` (the previous state is never mutated).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum
from typing import Final


class Event(str, Enum):
    START = "START"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    RESET = "RESET"
    COMPLETE_SESSION = "COMPLETE_SESSION"


# State name constants
IDLE: Final = "idle"
RUNNING_FOCUS: Final = "running_focus"
PAUSED_FOCUS: Final = "paused_focus"
RUNNING_SHORT_BREAK: Final = "running_short_break"
PAUSED_SHORT_BREAK: Final = "paused_short_break"
RUNNING_LONG_BREAK: Final = "running_long_break"
PAUSED_LONG_BREAK: Final = "paused_long_break"

_RUNNING_STATES: Final = frozenset(
    {RUNNING_FOCUS, RUNNING_SHORT_BREAK, RUNNING_LONG_BREAK}
)
_PAUSED_STATES: Final = frozenset(
    {PAUSED_FOCUS, PAUSED_SHORT_BREAK, PAUSED_LONG_BREAK}
)
_RUN_TO_PAUSE: Final = {
    RUNNING_FOCUS: PAUSED_FOCUS,
    RUNNING_SHORT_BREAK: PAUSED_SHORT_BREAK,
    RUNNING_LONG_BREAK: PAUSED_LONG_BREAK,
}
_PAUSE_TO_RUN: Final = {v: k for k, v in _RUN_TO_PAUSE.items()}


@dataclass(frozen=True)
class Config:
    """Pomodoro configuration (durations in minutes)."""

    focus_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    long_break_interval: int = 4

    def duration_seconds(self, state_name: str) -> int:
        if state_name in (RUNNING_FOCUS, PAUSED_FOCUS):
            return self.focus_minutes * 60
        if state_name in (RUNNING_SHORT_BREAK, PAUSED_SHORT_BREAK):
            return self.short_break_minutes * 60
        if state_name in (RUNNING_LONG_BREAK, PAUSED_LONG_BREAK):
            return self.long_break_minutes * 60
        return 0


@dataclass(frozen=True)
class State:
    """Immutable state of the pomodoro timer."""

    name: str = IDLE
    completed_focus_count: int = 0
    started_at: datetime | None = None
    remaining_seconds: int | None = None


class InvalidTransitionError(ValueError):
    """Raised when an event cannot be applied to the current state."""

    def __init__(self, state_name: str, event: Event) -> None:
        super().__init__(
            f"Invalid transition: event {event.value} not allowed in state '{state_name}'"
        )
        self.state_name = state_name
        self.event = event


def _next_phase_after_focus(completed_focus_count: int, config: Config) -> str:
    """Return the next running state after a focus session completes."""
    if config.long_break_interval <= 0:
        return RUNNING_SHORT_BREAK
    if completed_focus_count % config.long_break_interval == 0:
        return RUNNING_LONG_BREAK
    return RUNNING_SHORT_BREAK


def transition(
    current_state: State,
    event: Event | str,
    config: Config,
    now: datetime,
) -> State:
    """Compute the next state given the current state, event, config and time.

    This is a pure function: ``current_state`` is not mutated and no
    side effects are performed.

    Raises :class:`InvalidTransitionError` when the event is not valid
    for the current state.
    """
    if isinstance(event, str):
        try:
            event = Event(event)
        except ValueError as exc:  # pragma: no cover - defensive
            raise InvalidTransitionError(current_state.name, Event.RESET) from exc

    name = current_state.name

    if event is Event.RESET:
        return State(name=IDLE, completed_focus_count=0)

    if event is Event.START:
        if name != IDLE:
            raise InvalidTransitionError(name, event)
        return State(
            name=RUNNING_FOCUS,
            completed_focus_count=current_state.completed_focus_count,
            started_at=now,
            remaining_seconds=None,
        )

    if event is Event.PAUSE:
        if name not in _RUNNING_STATES:
            raise InvalidTransitionError(name, event)
        total = config.duration_seconds(name)
        elapsed = 0
        if current_state.started_at is not None:
            elapsed = int((now - current_state.started_at).total_seconds())
        remaining = max(0, total - elapsed)
        return replace(
            current_state,
            name=_RUN_TO_PAUSE[name],
            started_at=None,
            remaining_seconds=remaining,
        )

    if event is Event.RESUME:
        if name not in _PAUSED_STATES:
            raise InvalidTransitionError(name, event)
        remaining = current_state.remaining_seconds
        total = config.duration_seconds(name)
        if remaining is None:
            remaining = total
        # Reconstruct an equivalent ``started_at`` so callers can keep using
        # ``now - started_at`` to compute elapsed time.
        started_at = now - timedelta(seconds=total - remaining)
        return replace(
            current_state,
            name=_PAUSE_TO_RUN[name],
            started_at=started_at,
            remaining_seconds=None,
        )

    if event is Event.COMPLETE_SESSION:
        if name not in _RUNNING_STATES:
            raise InvalidTransitionError(name, event)
        if name == RUNNING_FOCUS:
            new_count = current_state.completed_focus_count + 1
            next_name = _next_phase_after_focus(new_count, config)
            return State(
                name=next_name,
                completed_focus_count=new_count,
                started_at=now,
                remaining_seconds=None,
            )
        # short/long break completed -> back to focus
        return State(
            name=RUNNING_FOCUS,
            completed_focus_count=current_state.completed_focus_count,
            started_at=now,
            remaining_seconds=None,
        )

    raise InvalidTransitionError(name, event)  # pragma: no cover - defensive


__all__ = [
    "Config",
    "Event",
    "InvalidTransitionError",
    "State",
    "transition",
    "IDLE",
    "RUNNING_FOCUS",
    "PAUSED_FOCUS",
    "RUNNING_SHORT_BREAK",
    "PAUSED_SHORT_BREAK",
    "RUNNING_LONG_BREAK",
    "PAUSED_LONG_BREAK",
]
