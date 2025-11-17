# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

import pygame

from tuxemon.event.eventbus import EventBus
from tuxemon.menu.alert import AlertManager
from tuxemon.prepare import CONFIG
from tuxemon.ui.text import TextArea


class TestAlertManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        font = pygame.font.Font(None, 16)
        self.text_area = TextArea(
            font=font,
            font_color=(255, 255, 255),
        )
        self.event_bus = EventBus()
        self.manager = AlertManager(self.event_bus)

    def test_alert_single_message(self):
        self.manager.alert("Hello World", self.text_area)
        self.assertTrue(self.manager.is_busy())
        self.assertEqual(self.text_area.text, "Hello World")

    def test_alert_split_lines(self):
        msg = "Line1\nLine2\nLine3"
        self.manager.alert(msg, self.text_area, split_lines=True)
        self.assertEqual(self.text_area.text, "Line1")
        self.manager.advance_dialog_line(CONFIG.dialog_speed, self.text_area)
        self.assertEqual(self.text_area.text, "Line2")
        self.manager.advance_dialog_line(CONFIG.dialog_speed, self.text_area)
        self.assertEqual(self.text_area.text, "Line3")

    def test_alert_queue_multiple(self):
        self.manager.alert("First", self.text_area)
        self.manager.alert("Second", self.text_area)
        self.assertEqual(self.text_area.text, "First")
        self.manager.dump_remaining_text(self.text_area)
        self.assertEqual(self.text_area.text, "Second")

    def test_callback_invoked(self):
        called = []

        def cb():
            called.append(True)

        self.manager.alert("Message", self.text_area, callback=cb)
        self.manager.dump_remaining_text(self.text_area)
        self.assertTrue(called)

    def test_callback_exception_handled(self):
        def bad_cb():
            raise ValueError("oops")

        self.manager.alert("Message", self.text_area, callback=bad_cb)
        self.manager.dump_remaining_text(self.text_area)
        self.assertFalse(self.manager.is_busy())

    def test_is_dialog_complete(self):
        self.text_area.text = "abc"
        self.text_area.drawing_text = True
        self.assertFalse(self.manager.is_dialog_complete(self.text_area))
        self.manager.dump_remaining_text(self.text_area)
        self.assertTrue(self.manager.is_dialog_complete(self.text_area))

    def test_current_message_none(self):
        self.assertIsNone(self.manager.current_message())

    def test_current_message_with_lines(self):
        self.manager.alert("Line1\nLine2", self.text_area, split_lines=True)
        self.assertEqual(self.manager.current_message(), "Line2")

    def test_update_progresses_text(self):
        self.manager.character_delay = 0.01
        self.text_area.text = "abc"
        self.text_area.drawing_text = True
        self.manager._time_accum = 0.05
        self.manager.update(0.05)
        self.assertTrue(self.text_area.text, "abc")

    def test_large_dt_consumes_all_text(self):
        self.manager.alert("abcdef", self.text_area)
        self.manager.character_delay = 0.01
        self.manager.update(10.0)
        self.assertFalse(self.text_area.drawing_text)

    def test_instant_dialog_speed(self):
        self.manager.alert(
            "Instant message", self.text_area, dialog_speed="instant"
        )
        self.assertEqual(self.text_area.text, "Instant message")
        self.manager.dump_remaining_text(self.text_area)
        self.assertTrue(self.manager.is_dialog_complete(self.text_area))

    def test_split_lines_instant_speed(self):
        msg = "Line1\nLine2\nLine3"
        self.manager.alert(
            msg,
            dialog_speed="instant",
            text_area=self.text_area,
            split_lines=True,
        )
        self.assertEqual(self.text_area.text, "Line1")
        self.manager.advance_dialog_line("instant", self.text_area)
        self.assertEqual(self.text_area.text, "Line2")
        self.manager.advance_dialog_line("instant", self.text_area)
        self.assertEqual(self.text_area.text, "Line3")
        self.manager.dump_remaining_text(self.text_area)
        self.assertTrue(self.manager.is_dialog_complete(self.text_area))

    def test_empty_queue_behavior(self):
        self.assertFalse(self.manager.is_busy())
        self.manager._process_next_alert()
        self.assertFalse(self.manager.is_busy())

    def test_busy_state_resets_after_alerts(self):
        self.manager.alert("Test message", self.text_area)
        self.assertTrue(self.manager.is_busy())
        self.manager.dump_remaining_text(self.text_area)
        self.assertFalse(self.manager.is_busy())

    def test_multiple_split_line_alerts(self):
        msg1 = "Line1a\nLine1b"
        msg2 = "Line2a\nLine2b"
        self.manager.alert(msg1, self.text_area, split_lines=True)
        self.manager.alert(msg2, self.text_area, split_lines=True)
        self.assertEqual(self.text_area.text, "Line1a")
        self.manager.advance_dialog_line(CONFIG.dialog_speed, self.text_area)
        self.assertEqual(self.text_area.text, "Line1b")
        self.manager.dump_remaining_text(self.text_area)
        self.assertEqual(self.text_area.text, "Line2a")

    def test_empty_message_alert(self):
        self.manager.alert("", self.text_area)
        self.assertEqual(self.text_area.text, "")
        self.manager.dump_remaining_text(self.text_area)
        self.assertTrue(self.manager.is_dialog_complete(self.text_area))
