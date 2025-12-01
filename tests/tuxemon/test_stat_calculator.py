# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock

from tuxemon.monster_dir.stats import (
    BasicStats,
    StatAnalyzer,
    StatCalculator,
    TemporaryStatBoosts,
    TrainingPoints,
)
from tuxemon.platform.const.sizes import COEFF_STATS
from tuxemon.shape import ShapeHandler
from tuxemon.taste import Taste


class TestStatCalculator(unittest.TestCase):

    def setUp(self):
        self.mock_shape = MagicMock(spec=ShapeHandler)
        self.mock_shape.attributes = BasicStats(
            armour=2, dodge=3, hp=5, melee=4, ranged=1, speed=2
        )

        self.mock_taste_cold = MagicMock(spec=Taste)
        self.mock_taste_cold.slug = "cold"
        self.mock_taste_cold.modifiers = [
            MagicMock(values=["speed"], multiplier=1.2),
            MagicMock(values=["hp"], multiplier=0.9),
        ]

        self.mock_taste_warm = MagicMock(spec=Taste)
        self.mock_taste_warm.slug = "warm"
        self.mock_taste_warm.modifiers = [
            MagicMock(values=["melee"], multiplier=1.1),
        ]

        self.modifiers = TemporaryStatBoosts(
            armour=1, dodge=0, hp=2, melee=0, ranged=0, speed=3
        )

        self.base_stats = BasicStats()
        self.training_points = TrainingPoints()
        self.level = 5

        self.calculator = StatCalculator(
            base_stats=self.base_stats,
            level=self.level,
            shape=self.mock_shape,
            taste_cold="cold",
            taste_warm="warm",
            modifiers=self.modifiers,
            training_points=self.training_points,
        )

        Taste.get_taste = MagicMock(
            side_effect=lambda name: {
                "cold": self.mock_taste_cold,
                "warm": self.mock_taste_warm,
            }[name]
        )

    def test_apply_base_stat_calculation(self):
        multiplier = self.level + COEFF_STATS
        stats = self.calculator.calculate_raw_stats(level=self.level)

        self.assertEqual(stats.armour, 2 * multiplier + 1)
        self.assertEqual(stats.dodge, 3 * multiplier + 0)
        self.assertEqual(stats.hp, 5 * multiplier + 2)
        self.assertEqual(stats.melee, 4 * multiplier + 0)
        self.assertEqual(stats.ranged, 1 * multiplier + 0)
        self.assertEqual(stats.speed, 2 * multiplier + 3)

    def test_apply_stat_updates(self):
        base_stats = BasicStats(
            armour=10, dodge=10, hp=100, melee=20, ranged=5, speed=30
        )
        updated = self.calculator.apply_stat_updates(
            base_stats, self.mock_taste_cold, self.mock_taste_warm
        )

        self.assertEqual(updated.hp, int(100 * 0.9))
        self.assertEqual(updated.speed, int(30 * 1.2))
        self.assertEqual(updated.melee, int(20 * 1.1))
        self.assertEqual(updated.armour, 10)
        self.assertEqual(updated.dodge, 10)
        self.assertEqual(updated.ranged, 5)

    def test_update_stat(self):
        result = self.calculator.update_stat(
            "speed", 50, self.mock_taste_cold, self.mock_taste_warm
        )
        self.assertEqual(result, int(50 * 1.2))

        result = self.calculator.update_stat(
            "melee", 40, self.mock_taste_cold, self.mock_taste_warm
        )
        self.assertEqual(result, int(40 * 1.1))

        result = self.calculator.update_stat(
            "armour", 20, self.mock_taste_cold, self.mock_taste_warm
        )
        self.assertEqual(result, 20)

    def test_calculate(self):
        final_stats = self.calculator.calculate()
        self.assertIsInstance(final_stats, BasicStats)
        self.assertGreater(final_stats.sum(), 0)

    def test_calculate_at_level(self):
        stats = self.calculator.calculate_at_level(10)
        self.assertIsInstance(stats, BasicStats)
        self.assertGreater(stats.sum(), 0)

    def test_calculate_at_level_invalid(self):
        with self.assertRaises(ValueError):
            self.calculator.calculate_at_level(0)

    def test_training_point_scaling(self):
        self.training_points.armour = 100
        stats = self.calculator.calculate_raw_stats(level=50)
        self.assertEqual(stats.armour, (2 * (50 + COEFF_STATS)) + 50 + 1)

    def test_negative_modifier(self):
        self.calculator.modifiers.hp = -10
        stats = self.calculator.calculate_raw_stats(level=self.level)
        self.assertLess(stats.hp, (5 * (self.level + COEFF_STATS)))

    def test_high_level_scaling(self):
        stats = self.calculator.calculate_raw_stats(level=1000)
        self.assertGreater(stats.sum(), 0)


class TestStatAnalyzer(unittest.TestCase):

    def setUp(self):
        self.mock_shape = MagicMock(spec=ShapeHandler)
        self.mock_shape.attributes = BasicStats(
            armour=2, dodge=3, hp=5, melee=4, ranged=1, speed=2
        )

        self.mock_taste_cold = MagicMock(spec=Taste)
        self.mock_taste_cold.slug = "cold"
        self.mock_taste_cold.modifiers = [
            MagicMock(values=["speed"], multiplier=1.2),
            MagicMock(values=["hp"], multiplier=0.9),
        ]

        self.mock_taste_warm = MagicMock(spec=Taste)
        self.mock_taste_warm.slug = "warm"
        self.mock_taste_warm.modifiers = [
            MagicMock(values=["melee"], multiplier=1.1),
        ]

        self.modifiers = TemporaryStatBoosts(
            armour=1, dodge=0, hp=2, melee=0, ranged=0, speed=3
        )

        self.base_stats = BasicStats()
        self.training_points = TrainingPoints()
        self.level = 5

        self.calculator = StatCalculator(
            base_stats=self.base_stats,
            level=self.level,
            shape=self.mock_shape,
            taste_cold="cold",
            taste_warm="warm",
            modifiers=self.modifiers,
            training_points=self.training_points,
        )

        Taste.get_taste = MagicMock(
            side_effect=lambda name: {
                "cold": self.mock_taste_cold,
                "warm": self.mock_taste_warm,
            }[name]
        )

        self.analyzer = StatAnalyzer(self.calculator)

    def test_get_breakdown_structure(self):
        breakdown = self.analyzer.get_breakdown()
        self.assertEqual(set(breakdown.keys()), set(BasicStats.names()))
        for stat, details in breakdown.items():
            self.assertIn("base_value", details)
            self.assertIn("training_points_raw", details)
            self.assertIn("training_points_scaled", details)
            self.assertIn("temporary_modifier", details)
            self.assertIn("pre_taste_total", details)
            self.assertIn("taste_multiplier", details)
            self.assertIn("final_value", details)

    def test_evaluate_taste_efficiency(self):
        score = self.analyzer.evaluate_taste_efficiency()
        self.assertIsInstance(score, float)

    def test_get_stat_growth_curve(self):
        curve = self.analyzer.get_stat_growth_curve(3)
        self.assertEqual(len(curve), 3)
        for level, stats in curve.items():
            self.assertIsInstance(level, int)
            self.assertIsInstance(stats, BasicStats)
            self.assertGreater(stats.sum(), 0)

    def test_get_stat_growth_curve_invalid(self):
        with self.assertRaises(ValueError):
            self.analyzer.get_stat_growth_curve(0)

    def test_taste_efficiency_normalized_range(self):
        score = self.analyzer.evaluate_taste_efficiency()
        self.assertGreaterEqual(score, -1.0)
        self.assertLessEqual(score, 1.0)

    def test_growth_curve_monotonic(self):
        curve = self.analyzer.get_stat_growth_curve(5)
        hp_values = [curve[level].hp for level in range(1, 6)]
        self.assertTrue(
            all(
                hp_values[i] <= hp_values[i + 1]
                for i in range(len(hp_values) - 1)
            )
        )

    def test_breakdown_matches_calculator(self):
        breakdown = self.analyzer.get_breakdown()
        final_stats = self.calculator.calculate()
        for stat in BasicStats.names():
            self.assertEqual(
                breakdown[stat]["final_value"], getattr(final_stats, stat)
            )

    def test_taste_multiplier_stacking(self):
        self.mock_taste_warm.modifiers = []
        self.mock_taste_cold.modifiers = [
            MagicMock(values=["hp"], multiplier=1.5),
            MagicMock(values=["hp"], multiplier=2.0),
        ]
        breakdown = self.analyzer.get_breakdown()
        self.assertAlmostEqual(
            breakdown["hp"]["taste_multiplier"], 1.5 * 2.0, places=2
        )
