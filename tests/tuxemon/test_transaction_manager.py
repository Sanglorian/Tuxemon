# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock, patch

from tuxemon.economy.shop_manager import ShopManager
from tuxemon.economy.transaction import TransactionManager
from tuxemon.item.item import INFINITE_ITEMS, Item
from tuxemon.money.manager import MoneyManager
from tuxemon.monster import Monster


class DummyBag:
    def __init__(self):
        self.items = {}

    def find_item(self, slug):
        return self.items.get(slug)

    def add_item(self, item, qty):
        self.items[item.slug] = item
        item.quantity = qty

    def remove_item(self, item, qty):
        if item.slug in self.items:
            item.quantity -= qty
            if item.quantity <= 0:
                del self.items[item.slug]


class DummyParty:
    def __init__(self):
        self.monsters = []

    def add_monster(self, monster):
        self.monsters.append(monster)

    def remove_monster(self, monster):
        self.monsters.remove(monster)


class DummyNPC:
    def __init__(self):
        self.bag = DummyBag()
        self.party = DummyParty()


class TestTransactionManager(unittest.TestCase):

    def setUp(self):
        self.buyer_money = MagicMock(spec=MoneyManager)
        self.seller_money = MagicMock(spec=MoneyManager)

        self.shop_manager = ShopManager()
        self.label = self.shop_manager.get_full_label("economy1", "potion")
        self.shop_manager.set_quantity(self.label, 5)

        self.tx = TransactionManager(
            self.buyer_money, self.seller_money, self.shop_manager
        )

        self.buyer = DummyNPC()
        self.seller = DummyNPC()

        self.item = MagicMock(spec=Item)
        self.item.slug = "potion"
        self.item.quantity = 5

        self.monster = MagicMock(spec=Monster)

    @patch("tuxemon.economy.transaction.Item.create")
    def test_buy_item_reduces_shop_and_buyer_pays(self, mock_create):
        mock_create.return_value = self.item
        # cost is total, not per unit
        self.tx.buy_item(self.buyer, self.item, 2, self.label, cost=10)
        self.assertEqual(self.shop_manager.get_quantity(self.label), 3)
        self.assertTrue(self.buyer.bag.find_item("potion"))
        self.assertEqual(self.buyer.bag.find_item("potion").quantity, 2)
        self.buyer_money.remove_money.assert_called_once_with(10)

    @patch("tuxemon.economy.transaction.Item.create")
    def test_buy_item_infinite_stock(self, mock_create):
        mock_create.return_value = self.item
        # mark shop stock as infinite
        self.shop_manager.set_quantity(self.label, INFINITE_ITEMS)
        self.tx.buy_item(self.buyer, self.item, 2, self.label, cost=5)
        self.assertEqual(
            self.shop_manager.get_quantity(self.label), INFINITE_ITEMS
        )
        self.buyer_money.remove_money.assert_called_with(5)

    def test_buy_monster(self):
        self.tx.buy_monster(self.buyer, self.monster, 1, self.label, cost=50)
        self.assertEqual(self.shop_manager.get_quantity(self.label), 4)
        self.assertIn(self.monster, self.buyer.party.monsters)
        self.buyer_money.remove_money.assert_called_with(50)

    def test_sell_item_increases_shop_and_seller_gets_paid(self):
        self.seller.bag.add_item(self.item, 2)
        self.tx.sell_item(
            self.seller, self.item, 1, amount=15, label=self.label
        )
        self.assertEqual(self.shop_manager.get_quantity(self.label), 6)
        self.seller_money.add_money.assert_called_once_with(15)

    def test_sell_monster(self):
        self.seller.party.add_monster(self.monster)
        self.tx.sell_monster(
            self.seller, self.monster, amount=25, label=self.label
        )
        self.assertEqual(self.shop_manager.get_quantity(self.label), 6)
        self.assertNotIn(self.monster, self.seller.party.monsters)
        self.seller_money.add_money.assert_called_once_with(25)

    @patch("tuxemon.economy.transaction.Item.create")
    def test_buy_item_not_enough_stock(self, mock_create):
        mock_create.return_value = self.item
        # now raises RuntimeError instead of silently reducing
        with self.assertRaises(RuntimeError):
            self.tx.buy_item(self.buyer, self.item, 10, self.label, cost=1)

    def test_sell_item_removes_from_bag(self):
        self.seller.bag.add_item(self.item, 1)
        self.tx.sell_item(
            self.seller, self.item, 1, amount=5, label=self.label
        )
        self.assertFalse(self.seller.bag.find_item("potion"))
