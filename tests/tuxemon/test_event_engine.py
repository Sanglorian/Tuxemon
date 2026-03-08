# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock, patch

import pytest

from tuxemon.client import LocalPygameClient
from tuxemon.db import BoundingBox, EventObject
from tuxemon.event.eventaction import ActionManager
from tuxemon.event.eventbehavior import BehaviorManager
from tuxemon.event.eventengine import EventEngine
from tuxemon.event.running import ConditionEvaluator, EventState
from tuxemon.map.manager import MapManager
from tuxemon.session import Session, local_session


@pytest.fixture
def event_engine():
    box = BoundingBox(x=0, y=0, width=1, height=1)
    action = MagicMock(spec=ActionManager)
    evaluator = MagicMock(spec=ConditionEvaluator)
    behavior = MagicMock(spec=BehaviorManager)
    eng = EventEngine(local_session, action, evaluator, behavior)
    eng._test_box = box
    return eng


def make_event(event_id, box):
    return EventObject(
        id=event_id,
        name="",
        priority=0,
        box=box,
        conds=[],
        acts=[],
    )


def test_init(event_engine):
    assert event_engine.current_map is None
    assert event_engine.running_events == {}
    assert event_engine.partial_events == []


def test_reset(event_engine):
    event_engine.running_events = {1: "event1", 2: "event2"}
    event_engine.current_map = "map1"
    event_engine.reset()
    assert event_engine.current_map is None
    assert event_engine.running_events == {}


def test_start_event(event_engine):
    event = make_event(1, event_engine._test_box)
    event_engine.session = MagicMock(spec=Session)
    event_engine.session.client = MagicMock(spec=LocalPygameClient)
    event_engine.session.client.map_manager = MagicMock(spec=MapManager)
    event_engine.session.client.map_manager.inits = []
    event_engine.start_event(event)
    assert 1 in event_engine.running_events


@pytest.mark.parametrize(
    "event_id",
    [
        pytest.param(99, id="id_99"),
        pytest.param(303, id="id_303"),
    ],
)
def test_register_global_event_prevents_duplicates(event_engine, event_id):
    event = make_event(event_id, event_engine._test_box)
    event_engine.global_events = [event]
    result = event_engine.register_global_event(event)
    assert result is False
    assert len(event_engine.global_events) == 1


@pytest.mark.parametrize(
    "event_id",
    [
        pytest.param(77, id="id_77"),
        pytest.param(404, id="id_404"),
    ],
)
def test_unregister_global_event(event_engine, event_id):
    event = make_event(event_id, event_engine._test_box)
    event_engine.global_events = [event]
    event_engine.triggered_global_events = {event_id}
    result = event_engine.unregister_global_event(event_id)
    assert result is True
    assert event not in event_engine.global_events
    assert event_id not in event_engine.triggered_global_events


def test_start_event_expands_behavior_actions(event_engine):
    event = make_event(1, event_engine._test_box)
    event_engine.behavior_manager = MagicMock()
    event_engine.session = MagicMock()
    event_engine.session.client = MagicMock()
    event_engine.session.client.map_manager = MagicMock()
    event_engine.session.client.map_manager.inits = []

    with patch("tuxemon.event.eventengine.expand_behavior_actions") as expand:
        expand.return_value = []
        event_engine.start_event(event)
        expand.assert_called_once_with(event, event_engine.behavior_manager)


def test_event_starts_only_when_conditions_met(event_engine):
    event = make_event(1, event_engine._test_box)
    cond = MagicMock()
    cond.check.return_value = True
    event.conds = [cond]
    event_engine.evaluator = MagicMock()
    event_engine.start_event = MagicMock()
    event_engine._evaluate_and_queue_event(event)

    event_engine.start_event.assert_called_once_with(event)


def test_event_does_not_start_when_conditions_fail(event_engine):
    event = make_event(1, event_engine._test_box)
    cond = MagicMock()
    event.conds = [cond]
    event_engine.evaluator.evaluate.return_value = False
    event_engine.start_event = MagicMock()
    event_engine._evaluate_and_queue_event(event)
    event_engine.start_event.assert_not_called()


def test_global_event_triggers_only_once(event_engine):
    event = make_event(1, event_engine._test_box)
    event.conds = [MagicMock()]
    event.conds[0].check.return_value = True
    event_engine.global_events = [event]
    event_engine.start_event = MagicMock()
    event_engine.check_global_conditions()
    event_engine.start_event.assert_called_once_with(event)
    event_engine.start_event.reset_mock()
    event_engine.check_global_conditions()
    event_engine.start_event.assert_not_called()


def test_completed_events_are_removed(event_engine):
    running = MagicMock()
    running.is_running.return_value = True
    running.process.return_value = False
    running.state = EventState.COMPLETED
    event_engine.running_events = {1: running}
    event_engine.update_running_events(0.1)
    assert event_engine.running_events == {}


def test_map_change_aborts_event_processing(event_engine):
    running = MagicMock()
    running.is_running.return_value = True

    def change_map(*args, **kwargs):
        event_engine.current_map = "mapB"
        return True

    running.process.side_effect = change_map
    event_engine.running_events = {1: running}
    event_engine.current_map = "mapA"
    event_engine.update_running_events(0.1)
    running.step.assert_called_once()


def test_cancel_event(event_engine):
    running = MagicMock()
    event_engine.running_events = {1: running}
    event_engine.cancel_event(1)
    running.cancel.assert_called_once()


def test_cancel_all_events(event_engine):
    r1 = MagicMock()
    r2 = MagicMock()
    event_engine.running_events = {1: r1, 2: r2}
    event_engine.cancel_all_events()
    r1.cancel.assert_called_once()
    r2.cancel.assert_called_once()
