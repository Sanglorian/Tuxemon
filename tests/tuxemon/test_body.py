# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.db import Direction
from tuxemon.entity import Body, Mover
from tuxemon.math import Point3, Vector3


class TestBody(unittest.TestCase):
    def setUp(self):
        self.body = Body(position=Point3(0, 0, 0))
        self.mover = Mover(self.body)

    def test_initialization(self):
        self.assertEqual(self.body.position, Point3(0, 0, 0))
        self.assertEqual(self.body.velocity, Vector3(0, 0, 0))
        self.assertEqual(self.body.acceleration, Vector3(0, 0, 0))
        self.assertEqual(self.mover.facing, Direction.down)

    def test_update_position(self):
        self.body.velocity = Vector3(1, 1, 0)
        self.body.acceleration = Vector3(1, 0, 0)
        self.body.update(time_delta=1.0)

        self.assertEqual(self.body.position, Point3(2, 1, 0))
        self.assertEqual(self.body.velocity, Vector3(2, 1, 0))

    def test_update_zero_time_delta(self):
        self.body.velocity = Vector3(5, 5, 5)
        self.body.update(time_delta=0.0)

        self.assertEqual(self.body.position, Point3(0, 0, 0))
        self.assertEqual(self.body.velocity, Vector3(5, 5, 5))

    def test_reset_selective(self):
        self.body.position = Point3(10, 10, 10)
        self.body.velocity = Vector3(5, 5, 5)
        self.body.acceleration = Vector3(1, 1, 1)

        self.body.reset(
            reset_position=False, reset_velocity=True, reset_acceleration=False
        )

        self.assertEqual(self.body.position, Point3(10, 10, 10))
        self.assertEqual(self.body.velocity, Vector3(0, 0, 0))
        self.assertEqual(self.body.acceleration, Vector3(1, 1, 1))

    def test_reset_all(self):
        self.body.position = Point3(15, 20, 30)
        self.body.velocity = Vector3(10, 15, 20)
        self.body.acceleration = Vector3(5, 5, 5)
        self.body.reset()

        self.assertEqual(self.body.position, Point3(0, 0, 0))
        self.assertEqual(self.body.velocity, Vector3(0, 0, 0))
        self.assertEqual(self.body.acceleration, Vector3(0, 0, 0))

    def test_stop(self):
        self.body.velocity = Vector3(5, 5, 5)
        self.mover.stop()
        self.assertEqual(self.body.velocity, Vector3(0, 0, 0))

    def test_move_with_valid_direction(self):
        self.mover.move(Vector3(0, -1, 0), speed=5)
        self.assertEqual(self.body.velocity, Vector3(0, -5, 0))
        self.assertEqual(self.mover.facing, Direction.up)

    def test_move_with_invalid_direction(self):
        with self.assertRaises(ValueError):
            self.mover.move(Vector3(1, 1, 1), speed=10)

    def test_move_boundary_case(self):
        self.mover.move(Vector3(0, 1, 0), speed=0.0001)
        self.assertEqual(self.body.velocity, Vector3(0, 0.0001, 0))
        self.assertEqual(self.mover.facing, Direction.down)

    def test_no_change_in_facing_when_stopping(self):
        self.mover.move(Vector3(1, 0, 0), speed=5)
        self.mover.stop()

        self.assertEqual(self.body.velocity, Vector3(0, 0, 0))
        self.assertEqual(self.mover.facing, Direction.right)

    def test_update_no_velocity_or_acceleration(self):
        self.body.update(time_delta=1.0)
        self.assertEqual(self.body.position, Point3(0, 0, 0))

    def test_reset_partial_attributes(self):
        self.body.position = Point3(10, 20, 30)
        self.body.velocity = Vector3(3, 2, 1)
        self.body.acceleration = Vector3(5, 5, 5)
        self.body.reset(
            reset_position=False, reset_velocity=True, reset_acceleration=False
        )
        self.assertEqual(self.body.position, Point3(10, 20, 30))
        self.assertEqual(self.body.velocity, Vector3(0, 0, 0))
        self.assertEqual(self.body.acceleration, Vector3(5, 5, 5))

    def test_update_with_extreme_time_delta(self):
        self.body.velocity = Vector3(1, 1, 1)
        self.body.update(time_delta=1000.0)
        self.assertEqual(self.body.position, Point3(1000, 1000, 1000))

    def test_update_position_boundary_values(self):
        self.body.velocity = Vector3(999999, 999999, 999999)
        self.body.update(time_delta=1.0)
        self.assertEqual(self.body.position, Point3(999999, 999999, 999999))


class TestMover(unittest.TestCase):
    def setUp(self):
        self.body = Body(position=Point3(0, 0, 0))
        self.mover = Mover(self.body)

    def test_move_with_valid_direction(self):
        self.mover.move(Vector3(1, 0, 0), speed=5)
        self.assertEqual(self.body.velocity, Vector3(5, 0, 0))
        self.assertEqual(self.mover.facing, Direction.right)

    def test_move_with_invalid_direction(self):
        with self.assertRaises(ValueError):
            self.mover.move(Vector3(0.5, 0.5, 0.5), speed=5)

    def test_stop(self):
        self.mover.move(Vector3(1, 0, 0), speed=5)
        self.mover.stop()
        self.assertEqual(self.body.velocity, Vector3(0, 0, 0))

    def test_move_with_zero_speed(self):
        self.mover.move(Vector3(0, 1, 0), speed=0)
        self.assertEqual(self.body.velocity, Vector3(0, 0, 0))
        self.assertEqual(self.mover.facing, Direction.down)

    def test_move_with_negative_speed(self):
        self.mover.move(Vector3(0, 1, 0), speed=-5)
        self.assertEqual(self.body.velocity, Vector3(0, -5, 0))
        self.assertEqual(self.mover.facing, Direction.down)

    def test_move_extreme_speed(self):
        self.mover.move(Vector3(1, 0, 0), speed=999999)
        self.assertEqual(self.body.velocity, Vector3(999999, 0, 0))
        self.assertEqual(self.mover.facing, Direction.right)

    def test_facing_consistency_after_stop(self):
        self.mover.move(Vector3(0, -1, 0), speed=5)
        self.mover.stop()
        self.assertEqual(self.mover.facing, Direction.up)

    def test_direction_map_integrity(self):
        self.assertEqual(
            self.mover.direction_map[tuple(Vector3(1, 0, 0).normalized)],
            Direction.right,
        )
        self.assertEqual(
            self.mover.direction_map[tuple(Vector3(-1, 0, 0).normalized)],
            Direction.left,
        )
        self.assertEqual(
            self.mover.direction_map[tuple(Vector3(0, 1, 0).normalized)],
            Direction.down,
        )
        self.assertEqual(
            self.mover.direction_map[tuple(Vector3(0, -1, 0).normalized)],
            Direction.up,
        )
