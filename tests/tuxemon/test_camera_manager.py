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
        self.manager.add_camera("cam1", self.camera1)
        self.assertIn("cam1", self.manager.cameras)
        self.assertEqual(self.manager.active_camera, self.camera1)
        self.assertIsInstance(self.manager.controller, CameraController)

    def test_add_camera_does_not_override_active(self):
        self.manager.add_camera("cam1", self.camera1)
        self.manager.add_camera("cam2", self.camera2)
        self.assertEqual(self.manager.active_camera, self.camera1)

    def test_set_active_camera_switches_control(self):
        self.manager.add_camera("cam1", self.camera1)
        self.manager.add_camera("cam2", self.camera2)
        self.manager.set_active_camera("cam2")
        self.assertEqual(self.manager.active_camera, self.camera2)
        self.assertIsInstance(self.manager.controller, CameraController)
        self.assertEqual(self.manager.controller.camera, self.camera2)

    def test_set_active_camera_raises_if_unmanaged(self):
        with self.assertRaises(ValueError):
            self.manager.set_active_camera("camX")

    def test_update_calls_active_camera_update(self):
        self.manager.add_camera("cam1", self.camera1)
        self.manager.update(0.1)
        self.camera1.update.assert_called_once_with(0.1)

    def test_handle_input_delegates_to_controller(self):
        self.manager.add_camera("cam1", self.camera1)
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
        self.manager.add_camera("cam1", self.camera1)
        self.assertEqual(self.manager.get_active_camera(), self.camera1)

    def test_remove_nonexistent_camera_raises(self):
        with self.assertRaises(ValueError):
            self.manager.remove_camera("camX")

    def test_remove_inactive_camera_leaves_active_intact(self):
        self.manager.add_camera("cam1", self.camera1)
        self.manager.add_camera("cam2", self.camera2)
        self.manager.remove_camera("cam2")
        self.assertEqual(self.manager.get_active_camera(), self.camera1)

    def test_remove_active_camera_clears_active(self):
        self.manager.add_camera("cam1", self.camera1)
        self.manager.remove_camera("cam1")
        self.assertIsNone(self.manager.get_active_camera())
        self.assertIsNone(self.manager.controller)

    def test_remove_active_camera_with_multiple_then_clear(self):
        self.manager.add_camera("cam1", self.camera1)
        self.manager.add_camera("cam2", self.camera2)
        self.manager.remove_camera("cam1")
        self.assertIsNone(self.manager.get_active_camera())
        self.assertIsNone(self.manager.controller)
        self.manager.set_active_camera("cam2")
        self.assertEqual(self.manager.get_active_camera(), self.camera2)


class IntegrationTestCameraManager(unittest.TestCase):
    def setUp(self):
        self.player = Mock()
        self.boundary = Mock()
        self.camera1 = Camera(self.player, self.boundary)
        self.camera2 = Camera(self.player, self.boundary)
        self.manager = CameraManager()

    def test_add_and_switch_real_cameras(self):
        self.manager.add_camera("cam1", self.camera1)
        self.manager.add_camera("cam2", self.camera2)

        self.assertEqual(self.manager.get_active_camera(), self.camera1)

        self.manager.set_active_camera("cam2")
        self.assertEqual(self.manager.get_active_camera(), self.camera2)
        self.assertIsInstance(self.manager.controller, CameraController)
        self.assertEqual(self.manager.controller.camera, self.camera2)


class StressTestCameraManager(unittest.TestCase):
    def setUp(self):
        self.manager = CameraManager()

    def test_add_and_remove_many_cameras(self):
        for i in range(100):
            cam = Mock(spec=Camera)
            self.manager.add_camera(f"cam{i}", cam)

        self.assertEqual(len(self.manager.cameras), 100)

        for i in range(100):
            self.manager.remove_camera(f"cam{i}")

        self.assertEqual(len(self.manager.cameras), 0)
        self.assertIsNone(self.manager.get_active_camera())
        self.assertIsNone(self.manager.controller)
