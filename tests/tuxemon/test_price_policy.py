# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock

from tuxemon.economy.price_policy import (
    PricePolicy,
    PricePolicyData,
    StaticYamlPolicy,
)
from tuxemon.item.item import Item
from tuxemon.monster import Monster


class PricePolicyTests(unittest.TestCase):
    def setUp(self):
        self.data = PricePolicyData(
            discount=0.2,  # 20% discount
            tax=0.1,  # 10% tax
            fee=5,  # transaction fee
            resell_bonus=0.1,  # 10% resale bonus
            resell_tax=0.05,  # 5% resale tax
            seller_fee=2,  # seller fee
        )
        self.policy = StaticYamlPolicy(self.data)

    def test_apply_modifiers_basic(self):
        final, discount = self.policy.apply_modifiers(100, 1, "item")
        # Base=100, taxed=110, discounted=88, +fee=93
        self.assertEqual(final, 93)
        self.assertEqual(discount, 20)

    def test_apply_modifiers_multiple_quantity(self):
        final, discount = self.policy.apply_modifiers(50, 3, "item")
        # Base=50, taxed=55, discounted=44, *3=132, +fee=137
        self.assertEqual(final, 137)
        self.assertEqual(discount, 20)

    def test_apply_modifiers_quantity_minus_one(self):
        final, discount = self.policy.apply_modifiers(100, -1, "item")
        # Base=100, taxed=110, discounted=88, +fee=93
        self.assertEqual(final, 93)
        self.assertEqual(discount, 20)

    def test_apply_resell_modifiers_basic(self):
        final, change = self.policy.apply_resell_modifiers(50, 1, "item")
        # Base=50, bonus=55, tax=52.25, +fee=54.25 → 54
        self.assertEqual(final, 54)
        self.assertEqual(change, 5)

    def test_apply_resell_modifiers_multiple_quantity(self):
        final, change = self.policy.apply_resell_modifiers(20, 2, "item")
        # Base=20, bonus=22, tax=20.9, *2=41.8, +fee=43.8 → 44
        self.assertEqual(final, 44)
        self.assertEqual(change, 4)

    def test_apply_resell_modifiers_quantity_minus_one(self):
        final, change = self.policy.apply_resell_modifiers(100, -1, "item")
        # Base=100, bonus=110, tax=104.5, +fee=106.5 → 107
        self.assertEqual(final, 107)
        self.assertEqual(change, 5)

    def test_discount_as_dict(self):
        data = PricePolicyData(
            discount={"item": 0.3, "default": 0.1},
            tax=0.0,
            fee=0,
            resell_bonus=0.0,
            resell_tax=0.0,
            seller_fee=0,
        )
        policy = StaticYamlPolicy(data)
        self.assertEqual(policy.get_discount("item"), 0.3)
        self.assertEqual(policy.get_discount("other"), 0.1)

    def test_zero_values(self):
        data = PricePolicyData(
            discount=0.0,
            tax=0.0,
            fee=0,
            resell_bonus=0.0,
            resell_tax=0.0,
            seller_fee=0,
        )
        policy = StaticYamlPolicy(data)
        final, discount = policy.apply_modifiers(100, 1, "item")
        self.assertEqual(final, 100)
        self.assertEqual(discount, 0)
        final, change = policy.apply_resell_modifiers(50, 1, "item")
        self.assertEqual(final, 50)
        self.assertEqual(change, 0)

    def test_negative_quantity(self):
        # Negative quantities should behave like -1 (special case)
        final, discount = self.policy.apply_modifiers(100, -1, "item")
        self.assertEqual(final, 93)
        final, change = self.policy.apply_resell_modifiers(50, -1, "item")
        self.assertEqual(final, 54)

    def test_base_class_defaults(self):
        base_policy = PricePolicy()
        final, discount = base_policy.apply_modifiers(100, 1, "item")
        self.assertEqual(final, 100)
        self.assertEqual(discount, 0)
        final, change = base_policy.apply_resell_modifiers(50, 1, "item")
        self.assertEqual(final, 50)
        self.assertEqual(change, 0)

    def test_buy_monster_with_policy(self):
        mock_monster = MagicMock(spec=Monster)
        mock_monster.slug = "rockitten"
        mock_monster.name = "rockitten"
        mock_monster.hp = 100

        # Base price = 100
        # Taxed = 110, discounted = 88, +fee = 93
        final, discount = self.policy.apply_modifiers(
            100, 1, mock_monster.slug
        )
        self.assertEqual(final, 93)
        self.assertEqual(discount, 20)

    def test_sell_monster_with_policy(self):
        mock_monster = MagicMock(spec=Monster)
        mock_monster.slug = "rockitten"
        mock_monster.name = "rockitten"
        mock_monster.hp = 100

        # Base cost = 50
        # Bonus = 55, tax = 52.25, +fee = 54.25 → 54
        final, change = self.policy.apply_resell_modifiers(
            50, 1, mock_monster.slug
        )
        self.assertEqual(final, 54)
        self.assertEqual(change, 5)

    def test_sell_monster_quantity_minus_one(self):
        mock_monster = MagicMock(spec=Monster)
        mock_monster.slug = "pairagrin"
        mock_monster.name = "pairagrin"
        mock_monster.hp = 20

        # Base cost = 20
        # Bonus = 22, tax = 20.9, +fee = 22.9 → 23
        final, change = self.policy.apply_resell_modifiers(
            20, -1, mock_monster.slug
        )
        self.assertEqual(final, 23)
        self.assertEqual(change, 4)
