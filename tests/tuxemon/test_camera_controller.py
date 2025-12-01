# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock

from tuxemon.camera.camera import Camera, CameraController
from tuxemon.platform.const import intentions


class TestCameraController(unittest.TestCase):
    def setUp(self):
        self.camera = MagicMock(spec=Camera)
        self.handler = CameraController(self.camera)

    def test_handle_input_free_roaming_held_up(self):
        self.camera.free_roaming_enabled = True
        event = MagicMock()
        event.held = True
        event.pressed = False
        event.button = intentions.UP
        self.handler.handle_input(event)
        self.camera.move.assert_called_once_with(dx=0, dy=-self.handler.speed)

    def test_handle_input_free_roaming_pressed_down(self):
        self.camera.free_roaming_enabled = True
        event = MagicMock()
        event.held = False
        event.pressed = True
        event.button = intentions.DOWN
        self.handler.handle_input(event)
        self.camera.move.assert_called_once_with(dx=0, dy=self.handler.speed)

    def test_handle_input_free_roaming_disabled(self):
        self.camera.free_roaming_enabled = False
        event = MagicMock()
        event.held = True
        event.button = intentions.UP
        self.handler.handle_input(event)
        self.camera.move.assert_not_called()

    def test_handle_input_return_event(self):
        self.camera.free_roaming_enabled = True
        event = MagicMock()
        event.held = True
        event.button = intentions.UP
        returned_event = self.handler.handle_input(event)
        self.assertEqual(event, returned_event)

    def test_handle_input_left(self):
        self.camera.free_roaming_enabled = True
        event = MagicMock()
        event.held = True
        event.button = intentions.LEFT
        self.handler.handle_input(event)
        self.camera.move.assert_called_once_with(dx=-self.handler.speed, dy=0)

    def test_handle_input_right(self):
        self.camera.free_roaming_enabled = True
        event = MagicMock()
        event.held = True
        event.button = intentions.RIGHT
        self.handler.handle_input(event)
        self.camera.move.assert_called_once_with(dx=self.handler.speed, dy=0)

    def test_handle_input_no_action(self):
        self.camera.free_roaming_enabled = True
        event = MagicMock()
        event.held = False
        event.pressed = False
        event.button = intentions.UP
        result = self.handler.handle_input(event)
        self.assertIsNone(result)
        self.camera.move.assert_not_called()

    def test_handle_input_invalid_direction(self):
        self.camera.free_roaming_enabled = True
        event = MagicMock()
        event.held = True
        event.button = 999  # Not a valid intention
        result = self.handler.handle_input(event)
        self.assertEqual(result, event)
        self.camera.move.assert_not_called()
