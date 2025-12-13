# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import Mock

from tuxemon.camera.camera import CameraTracker
from tuxemon.math import Vector2


class TestCameraTracker(unittest.TestCase):
    def setUp(self):
        self.view = Mock()
        self.view.get_size = Mock(return_value=(100, 80))
        self.view.screen_size = (100, 80)
        self.view.position = Vector2(50, 40)
        self.view.get_center = lambda pos: pos
        self.entity = Mock()
        self.entity.position = Vector2(10, 20)
        self.tracker = CameraTracker(self.view, self.entity)

    def test_initial_state(self):
        self.assertTrue(self.tracker.follows_entity)
        self.assertFalse(self.tracker.is_moving_smoothly)
        self.assertEqual(self.tracker.entity, self.entity)

    def test_update_centers_on_entity(self):
        self.entity.position = Vector2(30, 40)
        self.tracker.update(0.1)
        self.assertEqual(self.view.position, Vector2(30, 40))

    def test_update_returns_zero_vector(self):
        result = self.tracker.update(0.1)
        self.assertEqual(result, Vector2(0, 0))

    def test_update_calls_smooth_transition_when_flag_set(self):
        self.tracker.is_moving_smoothly = True
        self.tracker._update_smooth_transition = Mock()
        self.tracker.update(0.1)
        self.tracker._update_smooth_transition.assert_called_once_with(0.1)

    def test_set_entity_with_reset_snaps_camera(self):
        new_entity = Mock()
        new_entity.position = Vector2(99, 77)
        self.tracker.set_entity(new_entity, reset=True)
        self.assertEqual(self.view.position, Vector2(99, 77))

    def test_move_smoothly_to_sets_target_and_speed(self):
        target = Vector2(200, 200)
        self.view.position = Vector2(0, 0)
        self.tracker.move_smoothly_to(target, duration=2.0)
        self.assertTrue(self.tracker.is_moving_smoothly)
        self.assertEqual(self.tracker.target_position, target)
        self.assertGreater(self.tracker.transition_speed, 0)
