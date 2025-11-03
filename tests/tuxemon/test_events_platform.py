# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

from tuxemon.platform.events import (
    EventQueueHandler,
    InputHandler,
    PlayerInput,
)


class DummyInputHandler(InputHandler[Any]):
    def process_event(self, input_event: Any) -> None:
        pass


class DummyEventQueueHandler(EventQueueHandler):
    def process_events(self) -> Generator[PlayerInput, None, None]:
        for player_inputs in self._inputs.values():
            for input_handler in player_inputs.values():
                yield from input_handler.get_events()


class TestInputHandler(unittest.TestCase):

    def setUp(self):
        self.handler = DummyInputHandler(event_map={1: 1})

    def test_press_sets_value_and_hold_time(self):
        self.handler.press(1)
        inp = self.handler.buttons[1]
        self.assertEqual(inp.value, 1)
        self.assertEqual(inp.hold_time, 1)
        self.assertFalse(inp.triggered)

    def test_release_sets_value_and_triggered(self):
        self.handler.press(1)
        self.handler.release(1)
        inp = self.handler.buttons[1]
        self.assertEqual(inp.value, 0)
        self.assertEqual(inp.hold_time, 0)
        self.assertTrue(inp.triggered)

    def test_virtual_stop_events_yields_released_inputs(self):
        self.handler.press(1)
        events = list(self.handler.virtual_stop_events())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].button, 1)
        self.assertEqual(events[0].value, 0)

    def test_get_events_yields_copy_and_updates_state(self):
        self.handler.press(1)
        events = list(self.handler.get_events())
        self.assertEqual(events[0].hold_time, 1)
        self.assertTrue(events[0].pressed)

    def test_get_events_after_release(self):
        self.handler.press(1)
        self.handler.get_events()
        self.handler.release(1)
        events = list(self.handler.get_events())
        self.assertTrue(events[0].triggered)
        self.assertEqual(events[0].value, 0)

    def test_press_with_custom_value(self):
        self.handler.press(1, value=0.5)
        inp = self.handler.buttons[1]
        self.assertEqual(inp.value, 0.5)
        self.assertEqual(inp.hold_time, 1)

    def test_release_without_press(self):
        self.handler.release(1)
        inp = self.handler.buttons[1]
        self.assertEqual(inp.value, 0)
        self.assertEqual(inp.hold_time, 0)
        self.assertTrue(inp.triggered)

    def test_get_events_with_no_active_inputs(self):
        events = list(self.handler.get_events())
        self.assertEqual(events, [])

    def test_virtual_stop_events_with_no_held_buttons(self):
        events = list(self.handler.virtual_stop_events())
        self.assertEqual(events, [])

    def test_press_does_not_reset_hold_time(self):
        self.handler.press(1)
        list(self.handler.get_events())
        list(self.handler.get_events())
        self.handler.press(1)
        self.assertEqual(self.handler.buttons[1].hold_time, 3)

    def test_press_twice_does_not_reset_hold_time(self):
        self.handler.press(1)
        list(self.handler.get_events())
        list(self.handler.get_events())
        self.assertEqual(self.handler.buttons[1].hold_time, 3)

    def test_triggered_flag_resets_after_get_events(self):
        self.handler.press(1)
        self.handler.release(1)
        events = list(self.handler.get_events())
        self.assertTrue(events[0].triggered)
        self.assertFalse(self.handler.buttons[1].triggered)
        list(self.handler.get_events())
        self.assertFalse(self.handler.buttons[1].triggered)

    def test_invalid_button_press_raises(self):
        with self.assertRaises(ValueError):
            self.handler.press(99)

    def test_invalid_button_release_raises(self):
        with self.assertRaises(ValueError):
            self.handler.release(99)


class TestPlayerInput(unittest.TestCase):

    def test_pressed(self):
        input = PlayerInput(1, 1.0, 1)
        self.assertTrue(input.pressed)

    def test_held(self):
        input = PlayerInput(1, 1.0, 2)
        self.assertTrue(input.held)

    def test_not_pressed(self):
        input = PlayerInput(1, 0.0, 1)
        self.assertFalse(input.pressed)

    def test_not_held(self):
        input = PlayerInput(1, 1.0, 0)
        self.assertTrue(input.held)

    def test_triggered(self):
        input = PlayerInput(1, 1.0, 1)
        self.assertFalse(input.triggered)

    def test_not_triggered(self):
        input = PlayerInput(1, 1.0, 2)
        input.triggered = False
        self.assertFalse(input.triggered)


class TestPlayerInputEdgeCases(unittest.TestCase):

    def test_pressed_only_on_first_frame(self):
        inp = PlayerInput(1, value=1, hold_time=1)
        self.assertTrue(inp.pressed)
        inp.hold_time = 2
        self.assertFalse(inp.pressed)

    def test_released_only_when_value_goes_to_zero(self):
        inp = PlayerInput(1, value=0, previous_value=1)
        self.assertTrue(inp.released)
        inp.previous_value = 0
        self.assertFalse(inp.released)

    def test_held_long_requires_hold_time_gt_1(self):
        inp = PlayerInput(1, value=1, hold_time=1)
        self.assertFalse(inp.held_long)
        inp.hold_time = 2
        self.assertTrue(inp.held_long)

    def test_is_held_with_custom_threshold(self):
        inp = PlayerInput(1, value=1, hold_time=3)
        self.assertTrue(inp.is_held(2))
        self.assertFalse(inp.is_held(4))


class TestEventQueueHandler(unittest.TestCase):

    def setUp(self):
        self.queue = DummyEventQueueHandler()
        self.handler1 = DummyInputHandler(event_map={1: 1})
        self.handler2 = DummyInputHandler(event_map={2: 2})
        self.queue.add_input(player_id=0, index=0, input_handler=self.handler1)
        self.queue.add_input(player_id=1, index=0, input_handler=self.handler2)

    def test_process_events_single_press(self):
        self.handler1.press(1)
        events = list(self.queue.process_events())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].button, 1)
        self.assertTrue(events[0].pressed)

    def test_process_events_multiple_handlers(self):
        self.handler1.press(1)
        self.handler2.press(2)
        events = list(self.queue.process_events())
        self.assertEqual(len(events), 2)
        buttons = {e.button for e in events}
        self.assertIn(1, buttons)
        self.assertIn(2, buttons)

    def test_release_controls_generates_virtual_stops(self):
        self.handler1.press(1)
        events = list(self.queue.release_controls())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].button, 1)
        self.assertEqual(events[0].value, 0)

    def test_release_controls_multiple_handlers(self):
        self.handler1.press(1)
        self.handler2.press(2)
        events = list(self.queue.release_controls())
        self.assertEqual(len(events), 2)
        buttons = {e.button for e in events}
        self.assertIn(1, buttons)
        self.assertIn(2, buttons)

    def test_no_events_when_nothing_pressed(self):
        events = list(self.queue.process_events())
        self.assertEqual(events, [])

    def test_no_virtual_stops_when_nothing_held(self):
        events = list(self.queue.release_controls())
        self.assertEqual(events, [])

    def test_multiple_players_isolated_inputs(self):
        self.handler1.press(1)
        self.handler2.press(2)
        events = list(self.queue.process_events())
        buttons = {e.button for e in events}
        self.assertIn(1, buttons)
        self.assertIn(2, buttons)

    def test_release_controls_after_multiple_frames(self):
        self.handler1.press(1)
        list(self.queue.process_events())
        list(self.queue.process_events())
        events = list(self.queue.release_controls())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].button, 1)
        self.assertEqual(events[0].value, 0)

    def test_repeated_release_controls_no_duplicates(self):
        self.handler1.press(1)
        events1 = list(self.queue.release_controls())
        events2 = list(self.queue.release_controls())
        self.assertEqual(len(events1), 1)
        self.assertEqual(len(events2), 1)

    def test_press_release_press_cycle(self):
        self.handler1.press(1)
        list(self.queue.process_events())
        self.handler1.release(1)
        list(self.queue.process_events())
        self.handler1.press(1)
        events = list(self.queue.process_events())
        self.assertTrue(any(e.pressed for e in events))

    def test_hold_time_accumulates_across_frames(self):
        self.handler1.press(1)
        for _ in range(5):
            list(self.queue.process_events())
        self.assertEqual(self.handler1.buttons[1].hold_time, 6)

    def test_triggered_flag_only_set_on_release(self):
        self.handler1.press(1)
        list(self.queue.process_events())
        self.assertFalse(self.handler1.buttons[1].triggered)
        self.handler1.release(1)
        self.assertTrue(self.handler1.buttons[1].triggered)

    def test_clone_preserves_timestamp_and_state(self):
        self.handler1.press(1)
        original = self.handler1.buttons[1]
        clone = original.clone()
        self.assertEqual(clone.timestamp, original.timestamp)
        self.assertEqual(clone.value, original.value)
        self.assertEqual(clone.hold_time, original.hold_time)
        self.assertEqual(clone.previous_value, original.previous_value)

    def test_event_order_consistency(self):
        self.handler1.press(1)
        self.handler2.press(2)
        events = list(self.queue.process_events())
        self.assertEqual(events[0].button, 1)
        self.assertEqual(events[1].button, 2)
