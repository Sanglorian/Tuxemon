# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import Mock

from tuxemon.camera import Camera, CameraInputHandler
from tuxemon.platform.const import intentions


class TestCameraInputHandler(unittest.TestCase):
    def setUp(self):
        self.camera = Mock(spec=Camera)
        self.handler = CameraInputHandler(self.camera)

    def test_handle_input_free_roaming_held_up(self):
        self.camera.free_roaming_enabled = True
        event = Mock()
        event.held = True
        event.pressed = False
        event.button = intentions.UP
        self.handler.handle_input(event)
        self.camera.move_up.assert_called_once()

    def test_handle_input_free_roaming_pressed_down(self):
        self.camera.free_roaming_enabled = True
        event = Mock()
        event.held = False
        event.pressed = True
        event.button = intentions.DOWN
        self.handler.handle_input(event)
        self.camera.move_down.assert_called_once()

    def test_handle_input_free_roaming_disabled(self):
        self.camera.free_roaming_enabled = False
        event = Mock()
        event.held = True
        event.button = intentions.UP
        self.handler.handle_input(event)
        self.camera.move_up.assert_not_called()

    def test_handle_input_return_event(self):
        self.camera.free_roaming_enabled = True
        event = Mock()
        event.held = True
        event.button = intentions.UP
        returned_event = self.handler.handle_input(event)
        self.assertEqual(event, returned_event)

    def test_handle_input_left(self):
        self.camera.free_roaming_enabled = True
        event = Mock()
        event.held = True
        event.button = intentions.LEFT
        self.handler.handle_input(event)
        self.camera.move_left.assert_called_once()

    def test_handle_input_right(self):
        self.camera.free_roaming_enabled = True
        event = Mock()
        event.held = True
        event.button = intentions.RIGHT
        self.handler.handle_input(event)
        self.camera.move_right.assert_called_once()
