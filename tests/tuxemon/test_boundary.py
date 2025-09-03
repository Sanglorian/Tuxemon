# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.boundary import (
    BoundaryChecker,
    CircularBoundary,
    CompositeBoundary,
    RectangularBoundary,
)


class TestBoundaryChecker(unittest.TestCase):
    def setUp(self):
        self.checker = BoundaryChecker()

    def test_default_boundary_rejects_all(self):
        self.assertFalse(self.checker.is_within_boundaries((0, 0)))
        self.assertFalse(self.checker.is_within_boundaries((-1, -1)))

    def test_set_rectangular_boundary(self):
        self.checker.set_rectangular_boundary("map", 2, 6, 3, 8)
        self.assertTrue(self.checker.is_within_boundaries((3, 4)))
        self.assertFalse(self.checker.is_within_boundaries((1, 4)))
        self.assertFalse(self.checker.is_within_boundaries((6, 4)))
        self.assertFalse(self.checker.is_within_boundaries((3, 8)))

    def test_get_boundary_validity_rectangular(self):
        self.checker.set_rectangular_boundary("map", 0, 5, 0, 5)
        valid_x, valid_y = self.checker.get_boundary_validity((3, 4))
        self.assertTrue(valid_x)
        self.assertTrue(valid_y)

        valid_x, valid_y = self.checker.get_boundary_validity((6, 4))
        self.assertFalse(valid_x)
        self.assertTrue(valid_y)

    def test_get_boundary_validity_raises_on_non_rectangular(self):
        self.checker.set_circular_boundary("map", (5, 5), 3)
        with self.assertRaises(TypeError):
            self.checker.get_boundary_validity((5, 5))

    def test_set_circular_boundary(self):
        self.checker.set_circular_boundary("map", (10, 10), 5)
        self.assertTrue(self.checker.is_within_boundaries((10, 10)))
        self.assertTrue(self.checker.is_within_boundaries((13, 13)))
        self.assertFalse(self.checker.is_within_boundaries((16, 10)))
        self.assertFalse(self.checker.is_within_boundaries((10, 16)))

    def test_reset_to_default(self):
        self.checker.set_rectangular_boundary("map", 0, 10, 0, 10)
        self.assertTrue(self.checker.is_within_boundaries((5, 5)))
        self.checker.reset_to_default()
        self.assertFalse(self.checker.is_within_boundaries((5, 5)))

    def test_repr_contains_boundary_type(self):
        self.checker.set_rectangular_boundary("map", 0, 5, 0, 5)
        self.assertIn("RectangularBoundary", repr(self.checker))

        self.checker.set_circular_boundary("map", (5, 5), 2)
        self.assertIn("CircularBoundary", repr(self.checker))

    def test_default_boundary_rejects_all(self):
        self.assertFalse(self.checker.is_within_boundaries((0, 0)))
        self.assertFalse(self.checker.is_within_boundaries((-1, -1)))
        self.assertFalse(self.checker.is_within_boundaries((999, 999)))

    def test_reset_to_default_rejects_all(self):
        self.checker.set_rectangular_boundary("map", 0, 10, 0, 10)
        self.assertTrue(self.checker.is_within_boundaries((5, 5)))
        self.checker.reset_to_default()
        self.assertFalse(self.checker.is_within_boundaries((5, 5)))

    def test_repr_shows_reject_all_boundary(self):
        self.checker.reset_to_default()
        self.assertIn("NullBoundary", repr(self.checker))

    def test_rectangular_boundary_edges(self):
        width, height = 10, 10
        self.checker.set_rectangular_boundary("map", 0, width, 0, height)

        # Corners that should be valid
        self.assertTrue(self.checker.is_within_boundaries((0, 0)))  # top-left
        self.assertTrue(
            self.checker.is_within_boundaries((width - 1, 0))
        )  # top-right
        self.assertTrue(
            self.checker.is_within_boundaries((0, height - 1))
        )  # bottom-left
        self.assertTrue(
            self.checker.is_within_boundaries((width - 1, height - 1))
        )  # bottom-right

        # Edges that should be invalid (exclusive upper bounds)
        self.assertFalse(
            self.checker.is_within_boundaries((width, 5))
        )  # right edge
        self.assertFalse(
            self.checker.is_within_boundaries((5, height))
        )  # bottom edge
        self.assertFalse(
            self.checker.is_within_boundaries((width, height))
        )  # bottom-right corner out of bounds


class TestCompositeBoundary(unittest.TestCase):
    def test_union_combines_multiple_boundaries(self):
        rect = RectangularBoundary((0, 5), (0, 5))
        circle = CircularBoundary((10, 10), 3)
        combo = CompositeBoundary([rect, circle], mode="union")

        self.assertTrue(combo.is_within((2, 2)))  # Inside rectangle
        self.assertTrue(combo.is_within((10, 10)))  # Inside circle
        self.assertFalse(combo.is_within((7, 7)))  # Outside both

    def test_intersection_requires_all_boundaries(self):
        rect = RectangularBoundary((0, 10), (0, 10))
        circle = CircularBoundary((5, 5), 3)
        combo = CompositeBoundary([rect, circle], mode="intersection")

        self.assertTrue(combo.is_within((5, 5)))  # Inside both
        self.assertFalse(combo.is_within((9, 9)))  # Inside rect only
        self.assertFalse(combo.is_within((2, 2)))  # Inside circle only

    def test_empty_composite_union_returns_false(self):
        combo = CompositeBoundary([], mode="union")
        self.assertFalse(combo.is_within((0, 0)))

    def test_empty_composite_intersection_returns_true(self):
        combo = CompositeBoundary([], mode="intersection")
        self.assertTrue(combo.is_within((0, 0)))  # Vacuously true

    def test_invalid_mode_raises(self):
        with self.assertRaises(ValueError):
            CompositeBoundary([], mode="invalid")
