# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon import prepare
from tuxemon.camera.camera import CameraView, project
from tuxemon.math import Vector2


class TestCameraView(unittest.TestCase):
    def setUp(self):
        self.tile_size = prepare.TILE_SIZE
        self.screen_size = prepare.SCREEN_SIZE
        self.view = CameraView(
            tile_size=self.tile_size, screen_size=self.screen_size
        )

    def assertVectorEqual(self, actual: Vector2, expected: Vector2):
        self.assertEqual(actual.x, expected.x)
        self.assertEqual(actual.y, expected.y)

    def test_initial_position(self):
        self.assertVectorEqual(self.view.position, Vector2(0, 0))

    def test_set_position(self):
        target = Vector2(1.0, 1.0)
        projected = project((target.x, target.y))
        expected = Vector2(
            projected[0] + self.tile_size[0] // 2,
            projected[1] + self.tile_size[1] // 2,
        )
        self.view.set_position(target.x, target.y)
        self.assertVectorEqual(self.view.position, expected)

    def test_move_relative(self):
        self.view.position = Vector2(50, 50)
        self.view.move(dx=10, dy=-20)
        self.assertVectorEqual(self.view.position, Vector2(60, 30))

    def test_get_center_origin(self):
        projected = project((0.0, 0.0))
        expected = Vector2(
            projected[0] + self.tile_size[0] // 2,
            projected[1] + self.tile_size[1] // 2,
        )
        result = self.view.get_center(Vector2(0.0, 0.0))
        self.assertVectorEqual(result, expected)

    def test_get_center_whole_tile(self):
        position = Vector2(2.0, 3.0)
        projected = project((position.x, position.y))
        expected = Vector2(
            projected[0] + self.tile_size[0] // 2,
            projected[1] + self.tile_size[1] // 2,
        )
        result = self.view.get_center(position)
        self.assertVectorEqual(result, expected)

    def test_get_center_fractional_tile(self):
        position = Vector2(0.5, 0.5)
        projected = project((position.x, position.y))
        expected = Vector2(
            projected[0] + self.tile_size[0] // 2,
            projected[1] + self.tile_size[1] // 2,
        )
        result = self.view.get_center(position)
        self.assertVectorEqual(result, expected)

    def test_get_center_negative_coordinates(self):
        position = Vector2(-1.0, -1.0)
        projected = project((position.x, position.y))
        expected = Vector2(
            projected[0] + self.tile_size[0] // 2,
            projected[1] + self.tile_size[1] // 2,
        )
        result = self.view.get_center(position)
        self.assertVectorEqual(result, expected)

    def test_get_center_large_coordinates(self):
        position = Vector2(100.0, 200.0)
        projected = project((position.x, position.y))
        expected = Vector2(
            projected[0] + self.tile_size[0] // 2,
            projected[1] + self.tile_size[1] // 2,
        )
        result = self.view.get_center(position)
        self.assertVectorEqual(result, expected)

    def test_get_center_zero_tile_size(self):
        view = CameraView(tile_size=(0, 0), screen_size=self.screen_size)
        projected = project((1.0, 1.0))
        expected = Vector2(projected[0], projected[1])  # no offset
        result = view.get_center(Vector2(1.0, 1.0))
        self.assertVectorEqual(result, expected)

    def test_get_center_extreme_tile_size(self):
        tile_size = (1024, 512)
        view = CameraView(tile_size=tile_size, screen_size=self.screen_size)
        projected = project((1.0, 1.0))
        expected = Vector2(
            projected[0] + tile_size[0] // 2, projected[1] + tile_size[1] // 2
        )
        result = view.get_center(Vector2(1.0, 1.0))
        self.assertVectorEqual(result, expected)
