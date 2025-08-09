# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.math import Vector3


class TestVector3(unittest.TestCase):
    def test_initialization(self):
        v1 = Vector3()
        self.assertEqual(tuple(v1), (0, 0, 0))

        v2 = Vector3(1, 2, 3)
        self.assertEqual(tuple(v2), (1, 2, 3))

        v3 = Vector3([4, 5, 6])
        self.assertEqual(tuple(v3), (4, 5, 6))

    def test_addition(self):
        v1 = Vector3(1, 2, 3)
        v2 = Vector3(4, 5, 6)
        result = v1 + v2
        self.assertEqual(tuple(result), (5, 7, 9))

    def test_scalar_multiplication(self):
        v1 = Vector3(1, 2, 3)
        result = v1 * 2
        self.assertEqual(tuple(result), (2, 4, 6))

        result = 2 * v1
        self.assertEqual(tuple(result), (2, 4, 6))

    def test_iteration(self):
        v1 = Vector3(1, 2, 3)
        values = list(iter(v1))
        self.assertEqual(values, [1, 2, 3])

    def test_equality(self):
        v1 = Vector3(1, 2, 3)
        v2 = Vector3(1, 2, 3)
        v3 = Vector3(4, 5, 6)
        self.assertTrue(v1 == v2)
        self.assertFalse(v1 == v3)

    def test_getitem(self):
        v1 = Vector3(1, 2, 3)
        self.assertEqual(v1[0], 1)
        self.assertEqual(v1[1], 2)
        self.assertEqual(v1[2], 3)
        self.assertEqual(v1[0:2], (1, 2))

    def test_vector3_magnitude(self):
        v3 = Vector3(1, 2, 2)
        self.assertAlmostEqual(v3.magnitude, 3.0, places=2)

        v3_zero = Vector3(0, 0, 0)
        self.assertAlmostEqual(v3_zero.magnitude, 0.0, places=2)

        v3_large = Vector3(10, 10, 10)
        self.assertAlmostEqual(v3_large.magnitude, 17.32, places=2)

    def test_vector3_normalized(self):
        v3 = Vector3(1, 2, 2)
        normalized_v3 = v3.normalized
        self.assertAlmostEqual(normalized_v3.magnitude, 1.0, places=2)
        self.assertAlmostEqual(normalized_v3[0], 0.33, places=2)
        self.assertAlmostEqual(normalized_v3[1], 0.67, places=2)
        self.assertAlmostEqual(normalized_v3[2], 0.67, places=2)

        v3_zero = Vector3(0, 0, 0)
        normalized_v3_zero = v3_zero.normalized
        self.assertEqual(normalized_v3_zero.magnitude, 0.0)
