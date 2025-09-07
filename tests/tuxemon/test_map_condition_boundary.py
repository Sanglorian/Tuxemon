# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.boundary import Dimensions, MapConditionBoundary
from tuxemon.event import MapCondition


class TestMapConditionBoundary(unittest.TestCase):
    def test_tile_inside_condition(self):
        condition = MapCondition("", [], 0, 0, 5, 5, "", None)
        boundary = MapConditionBoundary(condition)
        self.assertTrue(boundary.is_within((2, 2)))

    def test_tile_outside_condition(self):
        condition = MapCondition("", [], 0, 0, 5, 5, "", None)
        boundary = MapConditionBoundary(condition)
        self.assertFalse(boundary.is_within((6, 6)))

    def test_tile_on_edge_condition(self):
        condition = MapCondition("", [], 0, 0, 5, 5, "", None)
        boundary = MapConditionBoundary(condition)
        self.assertTrue(boundary.is_within((0, 0)))  # Top-left
        self.assertTrue(boundary.is_within((4, 4)))  # Bottom-right

    def test_invalid_tile_position(self):
        condition = MapCondition("", [], 0, 0, 5, 5, "", None)
        boundary = MapConditionBoundary(condition)
        with self.assertRaises(TypeError):
            boundary.is_within("invalid")

    def test_edge_cases_for_condition_dimensions(self):
        condition = MapCondition("", [], 0, 0, 0, 0, "", None)
        boundary = MapConditionBoundary(condition)
        self.assertFalse(boundary.is_within((0, 0)))

        condition = MapCondition("", [], 0, 0, 1, 1, "", None)
        boundary = MapConditionBoundary(condition)
        self.assertTrue(boundary.is_within((0, 0)))

    def test_negative_coordinates(self):
        condition = MapCondition("", [], -2, -2, 5, 5, "", None)
        boundary = MapConditionBoundary(condition)
        self.assertTrue(boundary.is_within((0, 0)))

    def test_large_coordinates(self):
        condition = MapCondition("", [], 10000, 10000, 5, 5, "", None)
        boundary = MapConditionBoundary(condition)
        self.assertTrue(boundary.is_within((10001, 10001)))

    def test_edge_cases_zero_width_or_height(self):
        condition = MapCondition("", [], 0, 0, 0, 5, "", None)
        boundary = MapConditionBoundary(condition)
        self.assertFalse(boundary.is_within((0, 0)))

        condition = MapCondition("", [], 0, 0, 5, 0, "", None)
        boundary = MapConditionBoundary(condition)
        self.assertFalse(boundary.is_within((0, 0)))

    def test_move_shifts_boundary_position(self):
        condition = MapCondition("", [], 0, 0, 5, 5, "", None)
        boundary = MapConditionBoundary(condition)
        self.assertTrue(boundary.is_within((2, 2)))

        boundary.move(3, 3)
        self.assertFalse(boundary.is_within((2, 2)))
        self.assertTrue(boundary.is_within((5, 5)))
        self.assertEqual(boundary.get_center(), (5.5, 5.5))

    def test_resize_expands_boundary(self):
        condition = MapCondition("", [], 0, 0, 2, 2, "", None)
        boundary = MapConditionBoundary(condition)
        self.assertFalse(boundary.is_within((3, 3)))

        boundary.resize(2, 2)
        self.assertTrue(boundary.is_within((3, 3)))
        self.assertEqual(
            boundary.get_dimensions(), Dimensions(width=4.0, height=4.0)
        )

    def test_resize_contracts_boundary(self):
        condition = MapCondition("", [], 0, 0, 5, 5, "", None)
        boundary = MapConditionBoundary(condition)
        self.assertTrue(boundary.is_within((4, 4)))

        boundary.resize(-3, -3)
        self.assertFalse(boundary.is_within((4, 4)))
        self.assertEqual(
            boundary.get_dimensions(), Dimensions(width=2.0, height=2.0)
        )

    def test_resize_to_zero_dimensions(self):
        condition = MapCondition("", [], 0, 0, 2, 2, "", None)
        boundary = MapConditionBoundary(condition)
        boundary.resize(-2, -2)
        self.assertFalse(boundary.is_within((0, 0)))
        self.assertEqual(
            boundary.get_dimensions(), Dimensions(width=0.0, height=0.0)
        )

    def test_move_and_resize_combination(self):
        condition = MapCondition("", [], 0, 0, 3, 3, "", None)
        boundary = MapConditionBoundary(condition)
        boundary.move(2, 2)
        boundary.resize(2, 2)
        self.assertTrue(boundary.is_within((4, 4)))
        self.assertFalse(boundary.is_within((1, 1)))
        self.assertEqual(boundary.get_center(), (4.5, 4.5))
