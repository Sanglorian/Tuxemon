# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import Mock

from tuxemon.camera import Camera, CameraManager


class TestCameraManager(unittest.TestCase):
    def setUp(self):
        self.manager = CameraManager()
        self.camera1 = Mock(spec=Camera)
        self.camera2 = Mock(spec=Camera)

    def test_add_camera(self):
        self.manager.add_camera(self.camera1)
        self.assertIn(self.camera1, self.manager.cameras)
        self.assertEqual(self.manager.active_camera, self.camera1)

    def test_set_active_camera(self):
        self.manager.add_camera(self.camera1)
        self.manager.add_camera(self.camera2)
        self.manager.set_active_camera(self.camera2)
        self.assertEqual(self.manager.active_camera, self.camera2)

    def test_update(self):
        self.manager.add_camera(self.camera1)
        self.manager.update(0.1)
        self.camera1.update.assert_called_once()

    def test_handle_input(self):
        self.manager.add_camera(self.camera1)
        self.camera1.free_roaming_enabled = True
        event = Mock()
        self.manager.input_handler.handle_input = Mock()
        self.manager.handle_input(event)
        self.manager.input_handler.handle_input.assert_called_once_with(event)

    def test_get_active_camera(self):
        self.manager.add_camera(self.camera1)
        self.assertEqual(self.manager.get_active_camera(), self.camera1)
