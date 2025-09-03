# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import Mock

from pygame.rect import Rect

from tuxemon import prepare
from tuxemon.camera.camera import (
    SPEED_DOWN,
    SPEED_LEFT,
    SPEED_RIGHT,
    SPEED_UP,
    Camera,
    project,
    unproject,
)
from tuxemon.math import Vector2


class TestCamera(unittest.TestCase):
    def setUp(self):
        prepare.TILE_SIZE = (16, 16)
        self.entity = Mock()
        self.entity.position = Vector2(5.0, 5.0)
        self.boundary = Mock()
        self.boundary.get_boundary_validity.return_value = (True, True)
        self.camera = Camera(self.entity, self.boundary)
        projected = project((self.entity.position.x, self.entity.position.y))
        self.expected_center = Vector2(
            projected[0] + prepare.TILE_SIZE[0] // 2,
            projected[1] + prepare.TILE_SIZE[1] // 2,
        )

    def assertVectorEqual(self, actual: Vector2, expected: Vector2):
        self.assertEqual(actual.x, expected.x)
        self.assertEqual(actual.y, expected.y)

    def test_update_calls_tracker_and_effects(self):
        self.camera.tracker.update = Mock()
        self.camera.effects.update = Mock()
        self.camera.update(0.1)
        self.camera.tracker.update.assert_called_once_with(0.1)
        self.camera.effects.update.assert_called_once()

    def test_move_valid(self):
        self.camera.update(0.1)
        self.camera.move(dx=16, dy=16)
        self.assertEqual(self.camera.get_position(), Vector2(104, 104))

    def test_move_invalid_x(self):
        self.boundary.get_boundary_validity.return_value = (False, True)
        self.camera.update(0.1)
        self.camera.move(dx=16, dy=16)
        self.assertEqual(self.camera.get_position(), Vector2(88, 104))

    def test_move_invalid_y(self):
        self.boundary.get_boundary_validity.return_value = (True, False)
        self.camera.update(0.1)
        self.camera.move(dx=16, dy=16)
        self.assertEqual(self.camera.get_position(), Vector2(104, 88))

    def test_is_following(self):
        self.assertTrue(self.camera.is_following())
        self.camera.unfollow()
        self.assertFalse(self.camera.is_following())

    def test_set_position(self):
        self.camera.set_position(10.0, 10.0)
        self.assertEqual(self.camera.get_position(), Vector2(168, 168))

    def test_follow_and_unfollow(self):
        self.camera.unfollow()
        self.assertFalse(self.camera.is_following())
        self.camera.follow()
        self.assertTrue(self.camera.is_following())

    def test_move_up(self):
        self.camera.update(0.1)
        self.camera.move_up()
        self.assertEqual(self.camera.get_position().y, 88 - SPEED_UP)

    def test_move_down(self):
        self.camera.update(0.1)
        self.camera.move_down()
        self.assertEqual(self.camera.get_position().y, 88 + SPEED_DOWN)

    def test_move_left(self):
        self.camera.update(0.1)
        self.camera.move_left()
        self.assertEqual(self.camera.get_position().x, 88 - SPEED_LEFT)

    def test_move_right(self):
        self.camera.update(0.1)
        self.camera.move_right()
        self.assertEqual(self.camera.get_position().x, 88 + SPEED_RIGHT)

    def test_shake_triggers_effect(self):
        self.camera.effects.shake = Mock()
        self.camera.shake(2.0, 1.0)
        self.camera.effects.shake.assert_called_once_with(2.0, 1.0)

    def test_smooth_reset_to_entity_center(self):
        self.camera.tracker.move_smoothly_to = Mock()
        self.camera.smooth_reset_to_entity_center(duration=1.0)
        self.camera.tracker.move_smoothly_to.assert_called_once_with(
            Vector2(5.0, 5.0), 1.0
        )
        self.assertTrue(self.camera.tracker.pending_follow)

    def test_switch_to_entity(self):
        new_entity = Mock()
        new_entity.position = Vector2(10.0, 10.0)
        self.camera.switch_to_entity(new_entity)
        self.assertEqual(self.camera.tracker.entity, new_entity)
        self.assertTrue(self.camera.is_following())

    def test_switch_to_original_entity(self):
        new_entity = Mock()
        new_entity.position = Vector2(10.0, 10.0)
        self.camera.switch_to_entity(new_entity)
        self.camera.switch_to_original_entity()
        self.assertEqual(self.camera.tracker.entity, self.entity)
        self.assertTrue(self.camera.is_following())

    def test_reset_to_entity_center(self):
        self.camera.move(dx=10, dy=10)
        self.camera.reset_to_entity_center()
        self.assertEqual(self.camera.get_position(), self.expected_center)
        self.assertTrue(self.camera.is_following())
        self.assertFalse(self.camera.free_roaming_enabled)

    def test_move_smoothly_to(self):
        self.camera.tracker.move_smoothly_to = Mock()
        self.camera.move_smoothly_to(100.0, 200.0, duration=2.0)
        self.camera.tracker.move_smoothly_to.assert_called_once_with(
            Vector2(100.0, 200.0), 2.0
        )

    def test_get_position(self):
        self.camera.update(0.1)
        self.assertEqual(self.camera.get_position(), self.expected_center)

    def test_project_origin(self):
        self.assertEqual(project((0.0, 0.0)), (0, 0))

    def test_project_negative_coordinates(self):
        self.assertEqual(project((-1.0, -2.0)), (-16, -32))

    def test_project_fractional_coordinates(self):
        self.assertEqual(project((0.25, 0.75)), (4, 12))

    def test_project_large_coordinates(self):
        self.assertEqual(project((100.0, 200.0)), (1600, 3200))

    def test_unproject_origin(self):
        self.assertEqual(unproject((0, 0)), (0, 0))

    def test_unproject_negative_pixels(self):
        self.assertEqual(unproject((-16, -32)), (-1, -2))

    def test_unproject_fractional_pixels(self):
        self.assertEqual(unproject((4, 12)), (0, 0))  # int division truncates

    def test_unproject_large_pixels(self):
        self.assertEqual(unproject((1600, 3200)), (100, 200))

    def test_project_unproject_round_trip(self):
        original = (7.5, 3.25)
        projected = project(original)
        unprojected = unproject(projected)
        self.assertEqual(
            unprojected, (7, 3)
        )  # because unproject uses int division

    def test_get_viewport_returns_rect(self):
        viewport = self.camera.get_viewport()
        self.assertIsInstance(viewport, Rect)

    def test_viewport_center_matches_expected(self):
        self.camera.update(0.0)
        viewport = self.camera.get_viewport()
        center = Vector2(viewport.center)
        self.assertVectorEqual(center, self.expected_center)

    def test_viewport_top_left_calculation(self):
        self.camera.update(0.0)
        width, height = self.camera.view.get_size()
        expected_top_left = self.expected_center - Vector2(
            width // 2, height // 2
        )
        viewport = self.camera.get_viewport()
        self.assertEqual(
            viewport.topleft,
            (int(expected_top_left.x), int(expected_top_left.y)),
        )
