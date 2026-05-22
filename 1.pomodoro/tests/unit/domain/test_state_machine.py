"""Unit tests for the pomodoro domain state machine."""

from datetime import datetime, timedelta

import pytest

from pomodoro.domain.state_machine import (
    IDLE,
    PAUSED_FOCUS,
    PAUSED_SHORT_BREAK,
    RUNNING_FOCUS,
    RUNNING_LONG_BREAK,
    RUNNING_SHORT_BREAK,
    Config,
    Event,
    InvalidTransitionError,
    State,
    transition,
)


CONFIG = Config(
    focus_minutes=25,
    short_break_minutes=5,
    long_break_minutes=15,
    long_break_interval=4,
)
NOW = datetime(2026, 5, 22, 9, 0, 0)


def test_initial_state_is_idle() -> None:
    s = State()
    assert s.name == IDLE
    assert s.completed_focus_count == 0


def test_start_from_idle_enters_running_focus() -> None:
    s = transition(State(), Event.START, CONFIG, NOW)
    assert s.name == RUNNING_FOCUS
    assert s.started_at == NOW
    assert s.completed_focus_count == 0


def test_focus_complete_goes_to_short_break() -> None:
    s = State(name=RUNNING_FOCUS, completed_focus_count=0, started_at=NOW)
    next_state = transition(s, Event.COMPLETE_SESSION, CONFIG, NOW + timedelta(minutes=25))
    assert next_state.name == RUNNING_SHORT_BREAK
    assert next_state.completed_focus_count == 1


def test_fourth_focus_complete_goes_to_long_break() -> None:
    s = State(name=RUNNING_FOCUS, completed_focus_count=3, started_at=NOW)
    next_state = transition(s, Event.COMPLETE_SESSION, CONFIG, NOW)
    assert next_state.name == RUNNING_LONG_BREAK
    assert next_state.completed_focus_count == 4


def test_full_cycle_focus_break_pattern() -> None:
    """1,2,3 -> short_break; 4 -> long_break; cycle repeats."""
    state = State()
    state = transition(state, Event.START, CONFIG, NOW)
    expected_breaks = [
        RUNNING_SHORT_BREAK,
        RUNNING_SHORT_BREAK,
        RUNNING_SHORT_BREAK,
        RUNNING_LONG_BREAK,
        RUNNING_SHORT_BREAK,
        RUNNING_SHORT_BREAK,
        RUNNING_SHORT_BREAK,
        RUNNING_LONG_BREAK,
    ]
    for i, expected in enumerate(expected_breaks, start=1):
        state = transition(state, Event.COMPLETE_SESSION, CONFIG, NOW)
        assert state.name == expected, f"focus #{i} should go to {expected}"
        assert state.completed_focus_count == i
        # complete the break -> back to focus
        state = transition(state, Event.COMPLETE_SESSION, CONFIG, NOW)
        assert state.name == RUNNING_FOCUS


def test_short_break_complete_returns_to_focus() -> None:
    s = State(name=RUNNING_SHORT_BREAK, completed_focus_count=1, started_at=NOW)
    next_state = transition(s, Event.COMPLETE_SESSION, CONFIG, NOW)
    assert next_state.name == RUNNING_FOCUS
    assert next_state.completed_focus_count == 1


def test_long_break_complete_returns_to_focus() -> None:
    s = State(name=RUNNING_LONG_BREAK, completed_focus_count=4, started_at=NOW)
    next_state = transition(s, Event.COMPLETE_SESSION, CONFIG, NOW)
    assert next_state.name == RUNNING_FOCUS
    assert next_state.completed_focus_count == 4


def test_pause_from_running_focus_computes_remaining() -> None:
    s = State(name=RUNNING_FOCUS, started_at=NOW)
    paused = transition(s, Event.PAUSE, CONFIG, NOW + timedelta(minutes=10))
    assert paused.name == PAUSED_FOCUS
    assert paused.remaining_seconds == 15 * 60
    assert paused.started_at is None


def test_resume_from_paused_restores_running() -> None:
    paused = State(name=PAUSED_FOCUS, remaining_seconds=15 * 60)
    resumed = transition(paused, Event.RESUME, CONFIG, NOW)
    assert resumed.name == RUNNING_FOCUS
    assert resumed.remaining_seconds is None
    total = CONFIG.focus_minutes * 60
    elapsed = total - 15 * 60
    assert resumed.started_at == NOW - timedelta(seconds=elapsed)


def test_pause_resume_does_not_lose_time() -> None:
    state = transition(State(), Event.START, CONFIG, NOW)
    paused_at = NOW + timedelta(minutes=10)
    state = transition(state, Event.PAUSE, CONFIG, paused_at)
    assert state.remaining_seconds == 15 * 60
    resumed_at = paused_at + timedelta(minutes=3)
    state = transition(state, Event.RESUME, CONFIG, resumed_at)
    assert state.name == RUNNING_FOCUS
    assert (resumed_at - state.started_at) == timedelta(minutes=10)


def test_reset_from_any_state_returns_idle() -> None:
    for s in [
        State(),
        State(name=RUNNING_FOCUS, completed_focus_count=2, started_at=NOW),
        State(name=PAUSED_SHORT_BREAK, completed_focus_count=1, remaining_seconds=60),
        State(name=RUNNING_LONG_BREAK, completed_focus_count=4, started_at=NOW),
    ]:
        result = transition(s, Event.RESET, CONFIG, NOW)
        assert result == State(name=IDLE, completed_focus_count=0)


def test_resume_invalid_from_idle() -> None:
    with pytest.raises(InvalidTransitionError):
        transition(State(), Event.RESUME, CONFIG, NOW)


def test_pause_invalid_from_idle() -> None:
    with pytest.raises(InvalidTransitionError):
        transition(State(), Event.PAUSE, CONFIG, NOW)


def test_complete_invalid_from_idle() -> None:
    with pytest.raises(InvalidTransitionError):
        transition(State(), Event.COMPLETE_SESSION, CONFIG, NOW)


def test_start_invalid_from_running() -> None:
    s = State(name=RUNNING_FOCUS, started_at=NOW)
    with pytest.raises(InvalidTransitionError):
        transition(s, Event.START, CONFIG, NOW)


def test_resume_invalid_from_running() -> None:
    s = State(name=RUNNING_FOCUS, started_at=NOW)
    with pytest.raises(InvalidTransitionError):
        transition(s, Event.RESUME, CONFIG, NOW)


def test_pause_invalid_from_paused() -> None:
    s = State(name=PAUSED_FOCUS, remaining_seconds=600)
    with pytest.raises(InvalidTransitionError):
        transition(s, Event.PAUSE, CONFIG, NOW)


def test_transition_does_not_mutate_input() -> None:
    s = State(name=RUNNING_FOCUS, completed_focus_count=2, started_at=NOW)
    transition(s, Event.COMPLETE_SESSION, CONFIG, NOW)
    assert s.name == RUNNING_FOCUS
    assert s.completed_focus_count == 2
    assert s.started_at == NOW


def test_event_accepts_string() -> None:
    s = transition(State(), "START", CONFIG, NOW)
    assert s.name == RUNNING_FOCUS
