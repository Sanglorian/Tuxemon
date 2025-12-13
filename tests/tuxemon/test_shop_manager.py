# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.economy.shop_manager import ShopManager
from tuxemon.item.item import INFINITE_ITEMS


class TestShopManager(unittest.TestCase):

    def setUp(self):
        self.manager = ShopManager()

    def test_set_and_get_quantity(self):
        label = self.manager.get_full_label("economy1", "potion")
        self.manager.set_quantity(label, 5)
        self.assertEqual(self.manager.get_quantity(label), 5)

    def test_get_or_set_default_creates_entry(self):
        label = self.manager.get_full_label("economy1", "elixir")
        qty = self.manager.get_or_set_default(label, 10)
        self.assertEqual(qty, 10)
        self.assertEqual(self.manager.get_quantity(label), 10)

    def test_dump_and_load_roundtrip(self):
        label = self.manager.get_full_label("economy1", "ether")
        self.manager.set_quantity(label, 7)
        dumped = self.manager.dump_to_dict()
        self.assertIn(label, dumped)
        self.assertEqual(dumped[label]["quantity"], 7)
        reloaded = ShopManager.load_from_dict(dumped)
        self.assertEqual(reloaded.get_quantity(label), 7)

    def test_update_existing_quantity(self):
        label = self.manager.get_full_label("economy1", "revive")
        self.manager.set_quantity(label, 3)
        self.manager.set_quantity(label, 8)
        self.assertEqual(self.manager.get_quantity(label), 8)

    def test_infinite_stock_quantity(self):
        label = self.manager.get_full_label("economy1", "infinite_item")
        self.manager.set_quantity(label, INFINITE_ITEMS)
        self.assertEqual(self.manager.get_quantity(label), INFINITE_ITEMS)
        success = self.manager.decrease_stock(label, 10)
        self.assertTrue(success)
        self.assertEqual(self.manager.get_quantity(label), INFINITE_ITEMS)
        self.manager.increase_stock(label, 50)
        self.assertEqual(self.manager.get_quantity(label), INFINITE_ITEMS)

    def test_decrease_stock_success(self):
        label = self.manager.get_full_label("economy1", "antidote")
        self.manager.set_quantity(label, 5)
        success = self.manager.decrease_stock(label, 3)
        self.assertTrue(success)
        self.assertEqual(self.manager.get_quantity(label), 2)

    def test_decrease_stock_insufficient(self):
        label = self.manager.get_full_label("economy1", "rare_candy")
        self.manager.set_quantity(label, 2)
        success = self.manager.decrease_stock(label, 5)
        self.assertFalse(success)
        self.assertEqual(self.manager.get_quantity(label), 2)

    def test_increase_stock(self):
        label = self.manager.get_full_label("economy1", "super_potion")
        self.manager.set_quantity(label, 4)
        self.manager.increase_stock(label, 6)
        self.assertEqual(self.manager.get_quantity(label), 10)

    def test_get_max_affordable_quantity_with_finite_stock(self):
        label = self.manager.get_full_label("economy1", "pokeball")
        self.manager.set_quantity(label, 10)
        max_qty = self.manager.get_max_affordable_quantity(
            label, unit_price=2, buyer_money=15
        )
        self.assertEqual(max_qty, 7)

    def test_get_max_affordable_quantity_with_infinite_stock(self):
        label = self.manager.get_full_label("economy1", "ultra_ball")
        self.manager.set_quantity(label, INFINITE_ITEMS)
        max_qty = self.manager.get_max_affordable_quantity(
            label, unit_price=5, buyer_money=23
        )
        self.assertEqual(max_qty, 4)
