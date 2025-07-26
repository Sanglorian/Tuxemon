# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import random
import unittest
from unittest.mock import MagicMock

from tuxemon.formula import config_combat, speed_monster
from tuxemon.monster import Monster
from tuxemon.technique.technique import Technique


class TestSpeedTestFunction(unittest.TestCase):

    def setUp(self):
        self.config_combat = config_combat
        self.monster1 = self.create_monster(10.0, 5.0)
        self.monster2 = self.create_monster(15.0, 3.0)
        self.tech_fast = self.create_technique(2)
        self.tech_normal = self.create_technique(0)

    def create_monster(self, speed, dodge):
        monster = MagicMock(spec=Monster)
        monster.speed = speed
        monster.dodge = dodge
        return monster

    def create_technique(self, speed):
        technique = MagicMock(spec=Technique)
        technique.speed = speed
        return technique

    def _test_speed_modifier(self, monster, technique):
        results = [speed_monster(monster, technique) for _ in range(1000)]
        self.assertGreaterEqual(min(results), 1)
        self.assertLessEqual(
            max(results),
            monster.speed
            * (
                self.config_combat.base_speed_bonus
                + technique.speed * self.config_combat.speed_factor
            )
            + monster.dodge * self.config_combat.dodge_modifier
            + self.config_combat.speed_offset,
        )

    def test_speed_modifier_fast_technique(self):
        monster = self.create_monster(10.0, 5.0)
        technique = self.create_technique(2)
        self._test_speed_modifier(monster, technique)

    def test_speed_modifier_normal_technique(self):
        monster = self.create_monster(10.0, 5.0)
        technique = self.create_technique(0)
        self._test_speed_modifier(monster, technique)

    def test_speed_comparison_between_monsters(self):
        results1 = [
            speed_monster(self.monster1, self.tech_fast) for _ in range(1000)
        ]
        results2 = [
            speed_monster(self.monster2, self.tech_fast) for _ in range(1000)
        ]
        self.assertLessEqual(
            sum(results1) / len(results1), sum(results2) / len(results2)
        )

    def test_speed_with_different_speed_values(self):
        monster3 = self.create_monster(20.0, 5.0)
        results1 = [
            speed_monster(self.monster1, self.tech_fast) for _ in range(1000)
        ]
        results3 = [
            speed_monster(monster3, self.tech_fast) for _ in range(1000)
        ]
        self.assertGreater(
            sum(results3) / len(results3), sum(results1) / len(results1)
        )

    def test_speed_with_different_dodge_values(self):
        monster4 = self.create_monster(10.0, 10.0)
        results1 = [
            speed_monster(self.monster1, self.tech_fast) for _ in range(10000)
        ]
        results4 = [
            speed_monster(monster4, self.tech_fast) for _ in range(10000)
        ]
        self.assertGreater(
            sum(results4) / len(results4), sum(results1) / len(results1) * 0.9
        )

    def test_extreme_speed_and_dodge_values(self):
        monster5 = self.create_monster(1e6, 1.0)
        results1 = [
            speed_monster(self.monster1, self.tech_fast) for _ in range(1000)
        ]
        results5 = [
            speed_monster(monster5, self.tech_fast) for _ in range(1000)
        ]
        self.assertGreater(
            sum(results5) / len(results5), sum(results1) / len(results1)
        )

    def test_equal_speed_and_dodge(self):
        monster6 = self.create_monster(10.0, 5.0)
        results1 = [
            speed_monster(self.monster1, self.tech_fast) for _ in range(1000)
        ]
        results6 = [
            speed_monster(monster6, self.tech_fast) for _ in range(1000)
        ]
        self.assertLess(
            abs(sum(results6) / len(results6) - sum(results1) / len(results1)),
            5,
        )

    def test_fast_vs_normal_technique(self):
        random.seed(69)
        results1_fast = [
            speed_monster(self.monster1, self.tech_fast) for _ in range(1000)
        ]
        results1_normal = [
            speed_monster(self.monster1, self.tech_normal) for _ in range(1000)
        ]
        results2_fast = [
            speed_monster(self.monster2, self.tech_fast) for _ in range(1000)
        ]
        results2_normal = [
            speed_monster(self.monster2, self.tech_normal) for _ in range(1000)
        ]
        self.assertGreater(
            sum(results1_fast) / len(results1_fast),
            sum(results1_normal) / len(results1_normal),
        )
        self.assertGreater(
            sum(results2_fast) / len(results2_fast),
            sum(results2_normal) / len(results2_normal),
        )

    def test_speed_modifier_zero_speed(self):
        monster = self.create_monster(0.0, 5.0)
        technique = self.create_technique(2)
        results = [speed_monster(monster, technique) for _ in range(1000)]
        self.assertGreaterEqual(min(results), 1)

    def test_speed_modifier_negative_speed(self):
        monster = self.create_monster(-3.0, 5.0)
        technique = self.create_technique(2)
        results = [speed_monster(monster, technique) for _ in range(1000)]
        self.assertGreaterEqual(min(results), 1)

    def test_speed_modifier_zero_dodge(self):
        monster = self.create_monster(10.0, 0.0)
        technique = self.create_technique(2)
        results = [speed_monster(monster, technique) for _ in range(1000)]
        self.assertGreaterEqual(min(results), 1)

    def test_speed_modifier_negative_dodge(self):
        monster = self.create_monster(10.0, -3.0)
        technique = self.create_technique(2)
        results = [speed_monster(monster, technique) for _ in range(1000)]
        self.assertGreaterEqual(min(results), 1)

    def test_speed_modifier_zero_technique(self):
        monster = self.create_monster(10.0, 5.0)
        technique = self.create_technique(0)
        results = [speed_monster(monster, technique) for _ in range(1000)]
        self.assertGreaterEqual(min(results), 1)

    def test_speed_modifier_negative_technique(self):
        monster = self.create_monster(10.0, 5.0)
        technique = self.create_technique(-3)
        results = [speed_monster(monster, technique) for _ in range(1000)]
        self.assertGreaterEqual(min(results), 1)

    def test_speed_modifier_max_values(self):
        monster = self.create_monster(3.0, 3.0)
        technique = self.create_technique(3)
        results = [speed_monster(monster, technique) for _ in range(1000)]
        self.assertGreaterEqual(min(results), 1)

    def test_speed_modifier_min_values(self):
        monster = self.create_monster(-3.0, -3.0)
        technique = self.create_technique(-3)
        results = [speed_monster(monster, technique) for _ in range(1000)]
        self.assertGreaterEqual(min(results), 1)
