# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import Mock

from tuxemon.event.eventbus import EventBus
from tuxemon.event.eventmanager import EventManager
from tuxemon.platform.events import PlayerInput
from tuxemon.state.manager import StateManager


class TestEventManager(unittest.TestCase):
    def setUp(self):
        self.event_bus = Mock(spec=EventBus)
        self.state_manager = Mock(spec=StateManager)
        self.event_manager = EventManager(self.event_bus, self.state_manager)

    def test_init(self):
        self.assertEqual(self.event_manager._state_manager, self.state_manager)

    def test_process_events(self):
        events = []
        result = list(self.event_manager.process_events(events))
        self.assertEqual(result, [])

        events = [Mock(spec=PlayerInput), Mock(spec=PlayerInput)]
        self.state_manager.active_states = []
        result = list(self.event_manager.process_events(events))
        self.assertEqual(result, events)

        events = [Mock(spec=PlayerInput), Mock(spec=PlayerInput)]
        state = Mock()
        state.process_event = Mock(return_value=Mock(spec=PlayerInput))
        self.state_manager.active_states = [state]
        result = list(self.event_manager.process_events(events))
        self.assertEqual(len(result), len(events))

    def test_propagate_event(self):
        event = Mock(spec=PlayerInput)
        self.state_manager.active_states = []
        result = self.event_manager.propagate_event(event)
        self.assertEqual(result, event)

        event = Mock(spec=PlayerInput)
        state = Mock()
        state.process_event = Mock(return_value=event)
        self.state_manager.active_states = [state]
        result = self.event_manager.propagate_event(event)
        self.assertEqual(result, event)

        event = Mock(spec=PlayerInput)
        processed_event = Mock(spec=PlayerInput)
        state = Mock()
        state.process_event = Mock(return_value=processed_event)
        self.state_manager.active_states = [state]
        result = self.event_manager.propagate_event(event)
        self.assertEqual(result, processed_event)

        event = Mock(spec=PlayerInput)
        state = Mock()
        state.process_event = Mock(return_value=None)
        self.state_manager.active_states = [state]
        result = self.event_manager.propagate_event(event)
        self.assertIsNone(result)

    def test_release_controls(self):
        input_manager = Mock()
        input_manager.event_queue = Mock()
        input_manager.event_queue.release_controls = Mock(
            return_value=[Mock(spec=PlayerInput), Mock(spec=PlayerInput)]
        )
        self.state_manager.active_states = []
        result = self.event_manager.release_controls(input_manager)
        self.assertEqual(
            result,
            list(
                self.event_manager.process_events(
                    input_manager.event_queue.release_controls.return_value
                )
            ),
        )

    def test_middleware_preprocess_consumes_event(self):
        mw = Mock()
        mw.preprocess = Mock(return_value=None)
        mw.postprocess = Mock(return_value=None)
        self.event_manager.add_middleware(mw)

        events = [Mock(spec=PlayerInput)]
        result = list(self.event_manager.process_events(events))

        self.assertEqual(result, [])
        mw.preprocess.assert_called_once()

    def test_middleware_preprocess_modifies_event(self):
        modified_event = Mock(spec=PlayerInput)

        mw = Mock()
        mw.preprocess = Mock(return_value=modified_event)
        mw.postprocess = Mock(return_value=modified_event)
        self.event_manager.add_middleware(mw)

        events = [Mock(spec=PlayerInput)]
        self.state_manager.active_states = []
        result = list(self.event_manager.process_events(events))

        self.assertEqual(result, [modified_event])
        mw.preprocess.assert_called_once()
        mw.postprocess.assert_called_once()

    def test_middleware_postprocess_consumes_event(self):
        mw = Mock()
        mw.preprocess = Mock(side_effect=lambda e: e)
        mw.postprocess = Mock(return_value=None)
        self.event_manager.add_middleware(mw)

        events = [Mock(spec=PlayerInput)]
        self.state_manager.active_states = []
        result = list(self.event_manager.process_events(events))

        self.assertEqual(result, [])
        mw.postprocess.assert_called_once()

    def test_add_and_remove_middleware(self):
        mw = Mock()
        self.event_manager.add_middleware(mw)
        self.assertIn(mw, self.event_manager.middleware.values())

        self.event_manager.remove_middleware(mw)
        self.assertNotIn(mw, self.event_manager.middleware.values())


class TestEventManagerMiddleware(unittest.TestCase):

    def setUp(self):
        self.event_bus = Mock(spec=EventBus)
        self.state_manager = Mock(spec=StateManager)
        self.event_manager = EventManager(self.event_bus, self.state_manager)

    def test_preprocess_consumes_event(self):
        mw = Mock()
        mw.preprocess = Mock(return_value=None)
        mw.postprocess = Mock(return_value=None)
        self.event_manager.add_middleware(mw)

        events = [Mock(spec=PlayerInput)]
        result = list(self.event_manager.process_events(events))

        self.assertEqual(result, [])
        mw.preprocess.assert_called_once()

    def test_preprocess_modifies_event(self):
        modified_event = Mock(spec=PlayerInput)
        mw = Mock()
        mw.preprocess = Mock(return_value=modified_event)
        mw.postprocess = Mock(return_value=modified_event)
        self.event_manager.add_middleware(mw)

        events = [Mock(spec=PlayerInput)]
        self.state_manager.active_states = []
        result = list(self.event_manager.process_events(events))

        self.assertEqual(result, [modified_event])
        mw.preprocess.assert_called_once()
        mw.postprocess.assert_called_once()

    def test_postprocess_consumes_event(self):
        mw = Mock()
        mw.preprocess = Mock(side_effect=lambda e: e)
        mw.postprocess = Mock(return_value=None)
        self.event_manager.add_middleware(mw)

        events = [Mock(spec=PlayerInput)]
        self.state_manager.active_states = []
        result = list(self.event_manager.process_events(events))

        self.assertEqual(result, [])
        mw.postprocess.assert_called_once()

    def test_multiple_middleware_chain(self):
        mw1 = Mock()
        mw1.preprocess = Mock(side_effect=lambda e: e)
        mw1.postprocess = Mock(side_effect=lambda e: e)

        mw2 = Mock()
        mw2.preprocess = Mock(side_effect=lambda e: e)
        mw2.postprocess = Mock(side_effect=lambda e: None)

        self.event_manager.add_middleware(mw1)
        self.event_manager.add_middleware(mw2)

        events = [Mock(spec=PlayerInput)]
        self.state_manager.active_states = []
        result = list(self.event_manager.process_events(events))

        self.assertEqual(result, [])
        mw1.preprocess.assert_called_once()
        mw2.preprocess.assert_called_once()
        mw2.postprocess.assert_called_once()

    def test_add_and_remove_middleware(self):
        mw = Mock()
        self.event_manager.add_middleware(mw)
        self.assertIn(mw, self.event_manager.middleware.values())

        self.event_manager.remove_middleware(mw)
        self.assertNotIn(mw, self.event_manager.middleware.values())


class TestEventManagerEdgeCases(unittest.TestCase):

    def setUp(self):
        self.event_bus = Mock(spec=EventBus)
        self.state_manager = Mock(spec=StateManager)
        self.event_manager = EventManager(self.event_bus, self.state_manager)

    def test_empty_event_list(self):
        result = list(self.event_manager.process_events([]))
        self.assertEqual(result, [])

    def test_state_absorbs_event(self):
        event = Mock(spec=PlayerInput)
        state = Mock()
        state.process_event = Mock(return_value=None)
        self.state_manager.active_states = [state]

        result = list(self.event_manager.process_events([event]))
        self.assertEqual(result, [])

    def test_state_modifies_event(self):
        event = Mock(spec=PlayerInput)
        modified_event = Mock(spec=PlayerInput)
        state = Mock()
        state.process_event = Mock(return_value=modified_event)
        self.state_manager.active_states = [state]

        result = list(self.event_manager.process_events([event]))
        self.assertEqual(result, [modified_event])
