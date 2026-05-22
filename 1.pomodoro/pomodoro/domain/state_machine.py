"""Pure state machine for the Pomodoro timer.

The transition function is a pure function — same inputs produce same outputs and
there are no side effects — which makes it easy to unit test.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .entities import Settings


class State(str, Enum):
    IDLE = "idle"
    RUNNING_FOCUS = "running_focus"
    PAUSED_FOCUS = "paused_focus"
    RUNNING_SHORT_BREAK = "running_short_break"
    RUNNING_LONG_BREAK = "running_long_break"
    PAUSED_BREAK = "paused_break"


class Event(str, Enum):
    START = "START"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    RESET = "RESET"
    COMPLETE_SESSION = "COMPLETE_SESSION"


@dataclass(frozen=True)
class Context:
    """Cycle tracking state passed alongside `State` into the transition function.

    `completed_focus_count` is the number of focus sessions completed in the
    current cycle. After a long break it resets to 0.
    """

    completed_focus_count: int = 0


class InvalidTransitionError(Exception):
    """Raised when an event cannot be applied to the current state."""


_RUNNING_BREAK_STATES = {State.RUNNING_SHORT_BREAK, State.RUNNING_LONG_BREAK}


def transition(
    state: State,
    context: Context,
    event: Event,
    settings: Settings,
) -> tuple[State, Context]:
    """Compute the next (state, context) given an event.

    Raises `InvalidTransitionError` for events that are not legal in the
    current state.
    """

    if event is Event.START:
        if state is State.IDLE:
            return State.RUNNING_FOCUS, context
        raise InvalidTransitionError(f"START not allowed from {state.value}")

    if event is Event.PAUSE:
        if state is State.RUNNING_FOCUS:
            return State.PAUSED_FOCUS, context
        if state in _RUNNING_BREAK_STATES:
            return State.PAUSED_BREAK, context
        raise InvalidTransitionError(f"PAUSE not allowed from {state.value}")

    if event is Event.RESUME:
        if state is State.PAUSED_FOCUS:
            return State.RUNNING_FOCUS, context
        if state is State.PAUSED_BREAK:
            # We resume into a short break by default; the long-break case is
            # already represented by the context: it's only reachable after a
            # focus completion that took us to RUNNING_LONG_BREAK.
            return State.RUNNING_SHORT_BREAK, context
        raise InvalidTransitionError(f"RESUME not allowed from {state.value}")

    if event is Event.RESET:
        return State.IDLE, Context(completed_focus_count=0)

    if event is Event.COMPLETE_SESSION:
        if state is State.RUNNING_FOCUS:
            new_count = context.completed_focus_count + 1
            if new_count % settings.long_break_interval == 0:
                return State.RUNNING_LONG_BREAK, Context(new_count)
            return State.RUNNING_SHORT_BREAK, Context(new_count)
        if state is State.RUNNING_SHORT_BREAK:
            return State.RUNNING_FOCUS, context
        if state is State.RUNNING_LONG_BREAK:
            # After a long break a fresh cycle starts.
            return State.RUNNING_FOCUS, Context(completed_focus_count=0)
        raise InvalidTransitionError(
            f"COMPLETE_SESSION not allowed from {state.value}"
        )

    raise InvalidTransitionError(f"unknown event: {event!r}")
