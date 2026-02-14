# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import Mock

import pytest

from tuxemon.event.eventengine import EventState, RunningEvent


@pytest.fixture
def simple_event():
    return Mock(
        id=1,
        priority=5,
        delay=None,
        timeout=None,
    )


@pytest.fixture
def expanded_actions():
    return [1, 2, 3]


def test_init(simple_event, expanded_actions):
    event = RunningEvent(simple_event, expanded_actions)

    assert event.map_event is simple_event
    assert event.actions == expanded_actions
    assert event.context == {}
    assert event.action_index == 0
    assert event.current_action is None
    assert event.state == EventState.WAITING
    assert event.elapsed_time == 0.0


def test_get_next_action(simple_event, expanded_actions):
    event = RunningEvent(simple_event, expanded_actions)

    assert event.get_next_action() == 1
    event.advance()
    assert event.get_next_action() == 2
    event.advance()
    assert event.get_next_action() == 3
    event.advance()
    assert event.get_next_action() is None


def test_advance(simple_event, expanded_actions):
    event = RunningEvent(simple_event, expanded_actions)

    event.advance()
    assert event.action_index == 1

    event.advance()
    assert event.action_index == 2

    event.advance()
    assert event.action_index == 3  # end of list


def test_cancel(simple_event, expanded_actions):
    event = RunningEvent(simple_event, expanded_actions)
    event.cancel()

    assert event.state == EventState.CANCELLED
    assert event.is_cancelled()


def test_context(simple_event, expanded_actions):
    event = RunningEvent(simple_event, expanded_actions)

    event.context["a"] = 1
    assert event.context == {"a": 1}


def test_state_transitions(simple_event, expanded_actions):
    event = RunningEvent(simple_event, expanded_actions)

    assert event.state == EventState.WAITING

    event.running()
    assert event.state == EventState.RUNNING
    assert event.is_running()

    event.cancel()
    assert event.state == EventState.CANCELLED
    assert event.is_cancelled()


def test_tick_accumulates_elapsed_time(simple_event, expanded_actions):
    event = RunningEvent(simple_event, expanded_actions)

    assert event.elapsed_time == 0.0
    assert event.tick(1.5)
    assert event.elapsed_time == pytest.approx(1.5)

    assert event.tick(2.0)
    assert event.elapsed_time == pytest.approx(3.5)


def test_tick_respects_delay(expanded_actions):
    map_event = Mock(id=1, priority=5, timeout=None, delay=3.0)
    event = RunningEvent(map_event, expanded_actions)

    assert not event.tick(2.0)
    assert event.elapsed_time == 2.0

    assert event.tick(2.0)
    assert event.elapsed_time == 4.0


def test_tick_respects_timeout(expanded_actions):
    map_event = Mock(id=1, priority=5, timeout=5.0, delay=None)
    event = RunningEvent(map_event, expanded_actions)

    assert event.tick(4.0)
    assert not event.is_cancelled()

    assert not event.tick(2.0)
    assert event.is_cancelled()


def test_tick_delay_and_timeout_combined(expanded_actions):
    map_event = Mock(id=1, priority=5, timeout=8.0, delay=3.0)
    event = RunningEvent(map_event, expanded_actions)

    assert not event.tick(2.0)
    assert event.elapsed_time == 2.0

    assert event.tick(2.0)
    assert not event.is_cancelled()

    assert not event.tick(5.0)
    assert event.is_cancelled()


def test_tick_active_window(expanded_actions):
    map_event = Mock(id=1, priority=5, delay=3.0, timeout=8.0)
    event = RunningEvent(map_event, expanded_actions)

    assert not event.tick(2.0)
    assert not event.is_cancelled()

    assert event.tick(2.0)
    assert not event.is_cancelled()

    assert event.tick(3.0)
    assert not event.is_cancelled()

    assert not event.tick(2.0)
    assert event.is_cancelled()


def test_tick_active_window_with_context_flag(expanded_actions):
    map_event = Mock(id=1, priority=5, delay=3.0, timeout=8.0)
    event = RunningEvent(map_event, expanded_actions)

    assert not event.tick(2.0)
    assert "window_triggered" not in event.context

    ready = event.tick(2.0)
    assert ready
    if ready and not event.context.get("window_triggered"):
        event.context["window_triggered"] = True

    assert event.context["window_triggered"]

    ready = event.tick(2.0)
    assert ready
    assert event.context["window_triggered"]

    ready = event.tick(3.0)
    assert not ready
    assert event.is_cancelled()
