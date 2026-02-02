# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.client import LocalPygameClient
from tuxemon.db import BoundingBox, EventObject
from tuxemon.event.eventaction import ActionManager
from tuxemon.event.eventbehavior import BehaviorManager
from tuxemon.event.eventengine import EventEngine
from tuxemon.event.running import ConditionEvaluator
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


@pytest.mark.parametrize("event_id", [99, 303])
def test_register_global_event_prevents_duplicates(event_engine, event_id):
    event = make_event(event_id, event_engine._test_box)
    event_engine.global_events = [event]
    result = event_engine.register_global_event(event)
    assert result is False
    assert len(event_engine.global_events) == 1


@pytest.mark.parametrize("event_id", [77, 404])
def test_unregister_global_event(event_engine, event_id):
    event = make_event(event_id, event_engine._test_box)
    event_engine.global_events = [event]
    event_engine.triggered_global_events = {event_id}
    result = event_engine.unregister_global_event(event_id)
    assert result is True
    assert event not in event_engine.global_events
    assert event_id not in event_engine.triggered_global_events
