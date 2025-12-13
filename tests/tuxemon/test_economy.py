# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock

from tuxemon.db import EconomyItemModel, EconomyModel, EconomyMonsterModel
from tuxemon.economy.economy import Economy
from tuxemon.item.item import Item
from tuxemon.monster import Monster


class DummyNPC:
    def __init__(self, variables: dict[str, str]):
        self.game_variables = variables


class EconomyTestBase(unittest.TestCase):
    def setUp(self):
        self.economy = Economy()
        self.economy.model = EconomyModel(
            slug="test_economy",
            background="gfx/ui/item/item_menu_bg.png",
            resale_multiplier=0.5,
            items=[
                EconomyItemModel(
                    slug="potion",
                    price=20,
                    cost=5,
                    inventory=10,
                ),
                EconomyItemModel(slug="revive", price=100, cost=0),
                EconomyItemModel(slug="tuxeball", price=0, cost=10),
            ],
            monsters=[
                EconomyMonsterModel(
                    slug="rockitten",
                    level=5,
                    inventory=1,
                    price=100,
                    cost=50,
                ),
                EconomyMonsterModel(
                    slug="pairagrin",
                    level=1,
                    inventory=50,
                    price=10,
                    cost=2,
                ),
            ],
        )
        self.economy.refresh_maps()

    def test_update_item_field_with_valid_item(self):
        self.economy.update_entity_field("potion", "item", "price", 30)
        item = self.economy.get_item("potion")
        self.assertIsNotNone(item)
        self.assertEqual(item.price, 30)

    def test_update_item_field_with_unknown_item(self):
        with self.assertRaises(RuntimeError):
            self.economy.update_entity_field(
                "unknown_item", "item", "price", 30
            )

    def test_update_item_quantity_with_valid_item(self):
        self.economy.update_item_quantity("potion", 20)
        item = self.economy.get_item("potion")
        self.assertIsNotNone(item)
        self.assertEqual(item.inventory, 20)

    def test_update_item_quantity_with_unknown_item(self):
        with self.assertRaises(RuntimeError):
            self.economy.update_item_quantity("unknown_item", 20)

    def test_get_monster_valid(self):
        monster = self.economy.get_monster("rockitten")
        self.assertIsNotNone(monster)
        self.assertEqual(monster.level, 5)
        self.assertEqual(monster.inventory, 1)

    def test_get_monster_unknown(self):
        monster = self.economy.get_monster("unknown_monster")
        self.assertIsNone(monster)

    def test_refresh_maps_after_modification(self):
        new_item = EconomyItemModel(
            slug="tea", price=200, cost=50, inventory=5
        )
        self.economy.model.items.append(new_item)
        self.assertIsNone(self.economy.get_item("tea"))
        self.economy.refresh_maps()
        item = self.economy.get_item("tea")
        self.assertIsNotNone(item)
        self.assertEqual(item.price, 200)

    def test_variable_matches(self):
        npc = DummyNPC({"quest_stage": "start", "alignment": "good"})
        conditions = [{"quest_stage": "start"}, {"alignment": "good"}]
        self.assertTrue(self.economy.variable(conditions, npc))

    def test_variable_mismatch(self):
        npc = DummyNPC({"quest_stage": "start", "alignment": "evil"})
        conditions = [{"quest_stage": "start"}, {"alignment": "good"}]
        self.assertFalse(self.economy.variable(conditions, npc))

    def test_variable_partial_match(self):
        npc = DummyNPC({"quest_stage": "middle"})
        conditions = [{"quest_stage": "start"}]
        self.assertFalse(self.economy.variable(conditions, npc))

    def test_variable_empty_conditions(self):
        npc = DummyNPC({"quest_stage": "start"})
        conditions = []
        self.assertTrue(self.economy.variable(conditions, npc))

    def test_calculate_price_buy_item(self):
        mock_item = MagicMock(spec=Item)
        mock_item.slug = "potion"
        mock_item.cost = 5

        price, discount = self.economy.calculate_price(
            mock_item, quantity=2, seller_mode=False
        )
        self.assertEqual(price, 40)
        self.assertEqual(discount, 0)

    def test_calculate_price_sell_item(self):
        mock_item = MagicMock(spec=Item)
        mock_item.slug = "potion"
        mock_item.cost = 5

        price, discount = self.economy.calculate_price(
            mock_item, quantity=1, seller_mode=True
        )
        self.assertEqual(price, 5)
        self.assertEqual(discount, 0)

    def test_calculate_price_buy_monster(self):
        mock_monster = MagicMock(spec=Monster)
        mock_monster.slug = "rockitten"
        mock_monster.name = "rockitten"
        mock_monster.hp = 100

        price, discount = self.economy.calculate_price(
            mock_monster, quantity=1, seller_mode=False
        )
        self.assertEqual(price, 100)
        self.assertEqual(discount, 0)

    def test_calculate_price_sell_monster(self):
        mock_monster = MagicMock(spec=Monster)
        mock_monster.slug = "rockitten"
        mock_monster.name = "rockitten"
        mock_monster.hp = 100

        price, discount = self.economy.calculate_price(
            mock_monster, quantity=1, seller_mode=True
        )
        self.assertEqual(price, 50)
        self.assertEqual(discount, 0)

    def test_calculate_price_monster_without_model(self):
        mock_monster = MagicMock(spec=Monster)
        mock_monster.slug = "unknown_monster"
        mock_monster.name = "unknown_monster"
        mock_monster.hp = 20

        price, discount = self.economy.calculate_price(
            mock_monster, quantity=1, seller_mode=True
        )
        self.assertEqual(price, round(20 * 0.5))
