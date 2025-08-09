# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import Mock

from tuxemon.event.eventengine import RunningEvent


class TestRunningEvent(unittest.TestCase):
    def test_init(self):
        map_event = Mock(acts=[1, 2])
        event = RunningEvent(map_event)
        self.assertEqual(map_event, event.map_event)
        self.assertEqual({}, event.context)
        self.assertEqual(0, event.action_index)
        self.assertIsNone(event.current_action)
        self.assertIsNone(event.current_map_action)
        self.assertFalse(event.cancelled)

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
        self.assertTrue(event.cancelled)

    def test_context(self):
        map_event = Mock(acts=[1, 2])
        event = RunningEvent(map_event)
        event.context["a"] = 1
        self.assertEqual({"a": 1}, event.context)
