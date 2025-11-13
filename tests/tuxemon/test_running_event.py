# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import Mock

from tuxemon.event.eventengine import EventState, RunningEvent


class TestRunningEvent(unittest.TestCase):
    def test_init(self):
        map_event = Mock(acts=[1, 2])
        event = RunningEvent(map_event)
        self.assertEqual(map_event, event.map_event)
        self.assertEqual({}, event.context)
        self.assertEqual(0, event.action_index)
        self.assertIsNone(event.current_action)
        self.assertEqual(EventState.WAITING, event.state)

    def test_get_next_action(self):
        map_event = Mock(acts=[1, 2])
        event = RunningEvent(map_event)
        self.assertEqual(1, event.get_next_action())
        event.advance()
        self.assertEqual(2, event.get_next_action())
        event.advance()
        self.assertIsNone(event.get_next_action())

    def test_advance(self):
        map_event = Mock(acts=[1, 2])
        event = RunningEvent(map_event)
        event.advance()
        self.assertEqual(1, event.action_index)
        event.advance()
        self.assertEqual(2, event.action_index)

    def test_cancel(self):
        map_event = Mock(acts=[1, 2])
        event = RunningEvent(map_event)
        event.cancel()
        self.assertEqual(EventState.CANCELLED, event.state)
        self.assertTrue(event.is_cancelled())

    def test_context(self):
        map_event = Mock(acts=[1, 2])
        event = RunningEvent(map_event)
        event.context["a"] = 1
        self.assertEqual({"a": 1}, event.context)

    def test_state_transitions(self):
        map_event = Mock(acts=[1])
        event = RunningEvent(map_event)
        self.assertEqual(event.state, EventState.WAITING)

        event.running()
        self.assertEqual(event.state, EventState.RUNNING)
        self.assertTrue(event.is_running())

        event.cancel()
        self.assertEqual(event.state, EventState.CANCELLED)
        self.assertTrue(event.is_cancelled())

    def test_get_next_action_exhausted(self):
        map_event = Mock(acts=[1])
        event = RunningEvent(map_event)
        event.advance()
        self.assertIsNone(event.get_next_action())

    def test_cancel_all_events(self):
        map_event = Mock(acts=[1])
        event1 = RunningEvent(map_event)
        event2 = RunningEvent(map_event)
        event1.running()
        event2.running()

        manager = Mock()
        manager.running_events = {1: event1, 2: event2}
        manager.cancel_all_events = lambda: [
            e.cancel() for e in manager.running_events.values()
        ]

        manager.cancel_all_events()
        self.assertEqual(event1.state, EventState.CANCELLED)
        self.assertEqual(event2.state, EventState.CANCELLED)

    def test_context_persistence(self):
        map_event = Mock(acts=[1])
        event = RunningEvent(map_event)
        event.context["score"] = 42
        event.context["score"] += 8
        self.assertEqual(event.context["score"], 50)
