"""Unit tests for the pure-function state machine."""

from __future__ import annotations

import pytest

from pomodoro.domain.entities import Settings
from pomodoro.domain.state_machine import (
    Context,
    Event,
    InvalidTransitionError,
    State,
    transition,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        focus_minutes=25,
        short_break_minutes=5,
        long_break_minutes=15,
        long_break_interval=4,
    )


class TestStartTransitions:
    def test_start_from_idle_enters_running_focus(self, settings: Settings) -> None:
        state, ctx = transition(State.IDLE, Context(), Event.START, settings)
        assert state is State.RUNNING_FOCUS
        assert ctx == Context()

    def test_start_from_running_focus_is_invalid(self, settings: Settings) -> None:
        with pytest.raises(InvalidTransitionError):
            transition(State.RUNNING_FOCUS, Context(), Event.START, settings)


class TestPauseResume:
    def test_pause_focus(self, settings: Settings) -> None:
        state, _ = transition(State.RUNNING_FOCUS, Context(2), Event.PAUSE, settings)
        assert state is State.PAUSED_FOCUS

    def test_pause_break(self, settings: Settings) -> None:
        state, _ = transition(
            State.RUNNING_SHORT_BREAK, Context(1), Event.PAUSE, settings
        )
        assert state is State.PAUSED_BREAK

    def test_resume_focus(self, settings: Settings) -> None:
        state, _ = transition(State.PAUSED_FOCUS, Context(1), Event.RESUME, settings)
        assert state is State.RUNNING_FOCUS

    def test_resume_break(self, settings: Settings) -> None:
        state, _ = transition(State.PAUSED_BREAK, Context(1), Event.RESUME, settings)
        assert state is State.RUNNING_SHORT_BREAK

    def test_resume_from_idle_is_invalid(self, settings: Settings) -> None:
        # Bug-prevention: spec requires RESUME to be illegal from IDLE.
        with pytest.raises(InvalidTransitionError):
            transition(State.IDLE, Context(), Event.RESUME, settings)

    def test_pause_from_idle_is_invalid(self, settings: Settings) -> None:
        with pytest.raises(InvalidTransitionError):
            transition(State.IDLE, Context(), Event.PAUSE, settings)


class TestReset:
    @pytest.mark.parametrize(
        "state",
        [
            State.IDLE,
            State.RUNNING_FOCUS,
            State.PAUSED_FOCUS,
            State.RUNNING_SHORT_BREAK,
            State.RUNNING_LONG_BREAK,
            State.PAUSED_BREAK,
        ],
    )
    def test_reset_from_any_state(self, state: State, settings: Settings) -> None:
        next_state, ctx = transition(state, Context(3), Event.RESET, settings)
        assert next_state is State.IDLE
        assert ctx.completed_focus_count == 0


class TestCompleteSessionCycle:
    def test_first_focus_completes_into_short_break(self, settings: Settings) -> None:
        state, ctx = transition(
            State.RUNNING_FOCUS, Context(0), Event.COMPLETE_SESSION, settings
        )
        assert state is State.RUNNING_SHORT_BREAK
        assert ctx.completed_focus_count == 1

    def test_fourth_focus_completes_into_long_break(self, settings: Settings) -> None:
        state, ctx = transition(
            State.RUNNING_FOCUS, Context(3), Event.COMPLETE_SESSION, settings
        )
        assert state is State.RUNNING_LONG_BREAK
        assert ctx.completed_focus_count == 4

    def test_short_break_completes_back_to_focus(self, settings: Settings) -> None:
        state, ctx = transition(
            State.RUNNING_SHORT_BREAK, Context(1), Event.COMPLETE_SESSION, settings
        )
        assert state is State.RUNNING_FOCUS
        assert ctx.completed_focus_count == 1

    def test_long_break_resets_cycle_counter(self, settings: Settings) -> None:
        state, ctx = transition(
            State.RUNNING_LONG_BREAK, Context(4), Event.COMPLETE_SESSION, settings
        )
        assert state is State.RUNNING_FOCUS
        assert ctx.completed_focus_count == 0

    def test_complete_from_idle_is_invalid(self, settings: Settings) -> None:
        with pytest.raises(InvalidTransitionError):
            transition(State.IDLE, Context(), Event.COMPLETE_SESSION, settings)

    def test_full_cycle_focus_short_focus_short_focus_short_focus_long(
        self, settings: Settings
    ) -> None:
        """End-to-end transition trace for a full pomodoro cycle."""
        state = State.IDLE
        ctx = Context()

        state, ctx = transition(state, ctx, Event.START, settings)
        for i in range(1, 4):
            state, ctx = transition(state, ctx, Event.COMPLETE_SESSION, settings)
            assert state is State.RUNNING_SHORT_BREAK
            assert ctx.completed_focus_count == i
            state, ctx = transition(state, ctx, Event.COMPLETE_SESSION, settings)
            assert state is State.RUNNING_FOCUS

        state, ctx = transition(state, ctx, Event.COMPLETE_SESSION, settings)
        assert state is State.RUNNING_LONG_BREAK
        assert ctx.completed_focus_count == 4


class TestPurity:
    def test_transition_does_not_mutate_inputs(self, settings: Settings) -> None:
        ctx = Context(2)
        transition(State.RUNNING_FOCUS, ctx, Event.COMPLETE_SESSION, settings)
        # Frozen dataclass guarantees immutability, but assert anyway.
        assert ctx.completed_focus_count == 2
