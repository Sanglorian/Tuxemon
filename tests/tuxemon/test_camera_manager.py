# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import Mock

from tuxemon.camera.camera import Camera, CameraController, CameraManager


class TestCameraManager(unittest.TestCase):
    def setUp(self):
        self.manager = CameraManager()
        self.camera1 = Mock(spec=Camera)
        self.camera2 = Mock(spec=Camera)
        self.input_event = Mock()

    def test_add_camera_sets_active_if_none(self):
        self.manager.add_camera(self.camera1)
        self.assertIn(self.camera1, self.manager.cameras)
        self.assertEqual(self.manager.active_camera, self.camera1)
        self.assertIsInstance(self.manager.controller, CameraController)

    def test_add_camera_does_not_override_active(self):
        self.manager.add_camera(self.camera1)
        self.manager.add_camera(self.camera2)
        self.assertEqual(self.manager.active_camera, self.camera1)

    def test_set_active_camera_switches_control(self):
        self.manager.add_camera(self.camera1)
        self.manager.add_camera(self.camera2)
        self.manager.set_active_camera(self.camera2)
        self.assertEqual(self.manager.active_camera, self.camera2)
        self.assertIsInstance(self.manager.controller, CameraController)
        self.assertEqual(self.manager.controller.camera, self.camera2)

    def test_set_active_camera_raises_if_unmanaged(self):
        with self.assertRaises(ValueError):
            self.manager.set_active_camera(self.camera1)

    def test_update_calls_active_camera_update(self):
        self.manager.add_camera(self.camera1)
        self.manager.update(0.1)
        self.camera1.update.assert_called_once_with(0.1)

    def test_handle_input_delegates_to_controller(self):
        self.manager.add_camera(self.camera1)
        self.manager.controller.handle_input = Mock(
            return_value=self.input_event
        )
        result = self.manager.handle_input(self.input_event)
        self.manager.controller.handle_input.assert_called_once_with(
            self.input_event
        )
        self.assertEqual(result, self.input_event)

    def test_handle_input_returns_none_if_no_controller(self):
        result = self.manager.handle_input(self.input_event)
        self.assertIsNone(result)

    def test_get_active_camera_returns_correct_camera(self):
        self.manager.add_camera(self.camera1)
        self.assertEqual(self.manager.get_active_camera(), self.camera1)
