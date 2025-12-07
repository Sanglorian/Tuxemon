# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.event.eventmiddleware import (
    ButtonFilterMiddleware,
    EventMiddleware,
    InputTranslatorMiddleware,
    IntentionFilterMiddleware,
)
from tuxemon.platform.const import buttons, events, intentions
from tuxemon.platform.events import PlayerInput


class DummyMiddleware(EventMiddleware):
    def preprocess(self, event: PlayerInput):
        return event

    def postprocess(self, processed_event: PlayerInput):
        return processed_event


class TestEventMiddleware(unittest.TestCase):
    def test_cannot_instantiate_abstract(self):
        with self.assertRaises(TypeError):
            EventMiddleware()

    def test_subclass_must_implement_methods(self):
        mw = DummyMiddleware()
        event = PlayerInput(button="TEST", value=1, hold_time=0)
        self.assertEqual(mw.preprocess(event), event)
        self.assertEqual(mw.postprocess(event), event)

    def test_preprocess_can_consume_event(self):
        class ConsumingMiddleware(EventMiddleware):
            def preprocess(self, event: PlayerInput):
                return None

            def postprocess(self, processed_event: PlayerInput):
                return processed_event

        mw = ConsumingMiddleware()
        event = PlayerInput(button="TEST", value=1, hold_time=0)
        self.assertIsNone(mw.preprocess(event))

    def test_postprocess_can_consume_event(self):
        class ConsumingMiddleware(EventMiddleware):
            def preprocess(self, event: PlayerInput):
                return event

            def postprocess(self, processed_event: PlayerInput):
                return None

        mw = ConsumingMiddleware()
        event = PlayerInput(button="TEST", value=1, hold_time=0)
        self.assertIsNone(mw.postprocess(event))


class TestInputTranslatorMiddleware(unittest.TestCase):
    def setUp(self):
        self.mw = InputTranslatorMiddleware()

    def test_translate_known_button(self):
        event = PlayerInput(button=buttons.UP, value=1, hold_time=0)
        translated = self.mw.preprocess(event)
        self.assertEqual(translated.button, intentions.UP)

    def test_translate_unicode(self):
        event = PlayerInput(button=events.UNICODE, value="n", hold_time=0)
        translated = self.mw.preprocess(event)
        self.assertEqual(translated.button, intentions.NOCLIP)

    def test_unknown_button_passes_through(self):
        event = PlayerInput(button="UNKNOWN", value=1, hold_time=0)
        translated = self.mw.preprocess(event)
        self.assertEqual(translated.button, "UNKNOWN")

    def test_translate_other_known_buttons(self):
        event = PlayerInput(button=buttons.DOWN, value=1, hold_time=0)
        translated = self.mw.preprocess(event)
        self.assertEqual(translated.button, intentions.DOWN)

    def test_unicode_not_in_map_passes_through(self):
        event = PlayerInput(button=events.UNICODE, value="x", hold_time=0)
        translated = self.mw.preprocess(event)
        self.assertEqual(translated.button, events.UNICODE)
        self.assertEqual(translated.value, "x")

    def test_postprocess_returns_same_event(self):
        event = PlayerInput(button=buttons.LEFT, value=1, hold_time=0)
        processed = self.mw.postprocess(event)
        self.assertIs(processed, event)

    def test_postprocess_none(self):
        processed = self.mw.postprocess(None)
        self.assertIsNone(processed)

    def test_event_fields_preserved(self):
        event = PlayerInput(
            button=buttons.RIGHT,
            value=42,
            hold_time=3.5,
            previous_value=99,
            timestamp=1234567890.0,
            hold_duration=2.0,
        )
        translated = self.mw.preprocess(event)
        self.assertEqual(translated.value, 42)
        self.assertEqual(translated.hold_time, 3.5)
        self.assertEqual(translated.previous_value, 99)
        self.assertEqual(translated.timestamp, 1234567890.0)
        self.assertEqual(translated.hold_duration, 2.0)


class TestButtonFilterMiddleware(unittest.TestCase):
    def setUp(self):
        self.mw = ButtonFilterMiddleware()

    def test_event_passes_through_if_not_blocked(self):
        event = PlayerInput(button=buttons.UP, value=1, hold_time=0)
        processed = self.mw.preprocess(event)
        self.assertIs(processed, event)

    def test_event_blocked_if_in_blocklist(self):
        self.mw.block_button(buttons.UP)
        event = PlayerInput(button=buttons.UP, value=1, hold_time=0)
        processed = self.mw.preprocess(event)
        self.assertIsNone(processed)

    def test_unblock_button_allows_event(self):
        self.mw.block_button(buttons.UP)
        self.mw.unblock_button(buttons.UP)
        event = PlayerInput(button=buttons.UP, value=1, hold_time=0)
        processed = self.mw.preprocess(event)
        self.assertIs(processed, event)

    def test_initially_blocked_buttons_constructor(self):
        mw = ButtonFilterMiddleware(initially_blocked_buttons={buttons.DOWN})
        event = PlayerInput(button=buttons.DOWN, value=1, hold_time=0)
        processed = mw.preprocess(event)
        self.assertIsNone(processed)

    def test_postprocess_returns_event(self):
        event = PlayerInput(button=buttons.LEFT, value=1, hold_time=0)
        processed = self.mw.postprocess(event)
        self.assertIs(processed, event)

    def test_postprocess_none(self):
        processed = self.mw.postprocess(None)
        self.assertIsNone(processed)


class TestIntentionFilterMiddleware(unittest.TestCase):
    def setUp(self):
        self.mw = IntentionFilterMiddleware()

    def test_global_block_consumes_event(self):
        event = PlayerInput(button=intentions.UP, value=1, hold_time=0)
        processed = self.mw.preprocess(event)
        self.assertIsNone(processed)

    def test_allow_specific_action(self):
        self.mw.update_allowed_actions({intentions.UP})
        event = PlayerInput(button=intentions.UP, value=1, hold_time=0)
        processed = self.mw.preprocess(event)
        self.assertIs(processed, event)

    def test_block_unlisted_action(self):
        self.mw.update_allowed_actions({intentions.UP})
        event = PlayerInput(button=intentions.DOWN, value=1, hold_time=0)
        processed = self.mw.preprocess(event)
        self.assertIsNone(processed)

    def test_open_gate_allows_everything(self):
        self.mw.update_allowed_actions(IntentionFilterMiddleware.OPEN_GATE)
        event1 = PlayerInput(button=intentions.UP, value=1, hold_time=0)
        event2 = PlayerInput(button=intentions.DOWN, value=1, hold_time=0)
        self.assertIs(self.mw.preprocess(event1), event1)
        self.assertIs(self.mw.preprocess(event2), event2)

    def test_postprocess_returns_event(self):
        event = PlayerInput(button=intentions.LEFT, value=1, hold_time=0)
        processed = self.mw.postprocess(event)
        self.assertIs(processed, event)

    def test_postprocess_none(self):
        processed = self.mw.postprocess(None)
        self.assertIsNone(processed)
