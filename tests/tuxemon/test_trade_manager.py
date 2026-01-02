# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from tuxemon.trade_manager import TradeManager, TradeRecord, TradeResult


class MockPlayer:
    def __init__(self, name):
        self.name = name
        self.instance_id = uuid4()
        self.party = MagicMock()
        self.tuxepedia = MagicMock()


class MockMonster:
    def __init__(self, name, slug, owner):
        self.name = name
        self.slug = slug
        self.instance_id = uuid4()
        self.level = 5
        self._owner = owner

    def get_owner(self):
        return self._owner

    def set_owner(self, new_owner):
        self._owner = new_owner

    def set_acquisition(self, acquisition):
        self.acquisition = acquisition


class TradeManagerTest(unittest.TestCase):
    def setUp(self):
        self.manager = TradeManager()

        self.player_a = MockPlayer("Better")
        self.player_b = MockPlayer("Call")

        self.monster_a = MockMonster("Flamey", "flamey_slug", self.player_a)
        self.monster_b = MockMonster("Splashy", "splashy_slug", self.player_b)

        self.player_a.party.monsters = [self.monster_a]
        self.player_b.party.monsters = [self.monster_b]

    def test_execute_trade_success(self):
        result = self.manager.execute_trade(self.monster_a, self.monster_b)
        self.assertEqual(result, TradeResult.SUCCESS)
        self.assertEqual(len(self.manager.global_trade_log), 2)

    def test_execute_trade_same_owner(self):
        self.monster_b._owner = self.player_a
        result = self.manager.execute_trade(self.monster_a, self.monster_b)
        self.assertEqual(result, TradeResult.SAME_OWNER)

    def test_execute_trade_monster_not_found(self):
        self.player_a.party.monsters = []
        result = self.manager.execute_trade(self.monster_a, self.monster_b)
        self.assertEqual(result, TradeResult.NOT_FOUND)

    def test_was_traded_with_player(self):
        record = TradeRecord(
            from_player="Better",
            to_player="Call",
            from_player_id=self.player_a.instance_id,
            to_player_id=self.player_b.instance_id,
            monster_given="flamey_slug",
            monster_received="splashy_slug",
            monster_given_id=self.monster_a.instance_id,
            monster_received_id=self.monster_b.instance_id,
            timestamp=datetime.now(timezone.utc),
        )
        self.manager.global_trade_log.append(record)
        self.assertTrue(self.manager.was_traded_with_player("Better"))
        self.assertTrue(self.manager.was_traded_with_player("Call"))
        self.assertFalse(self.manager.was_traded_with_player("Saul"))

    def test_was_traded_for_monster(self):
        record = TradeRecord(
            from_player="Better",
            to_player="Call",
            from_player_id=self.player_a.instance_id,
            to_player_id=self.player_b.instance_id,
            monster_given="flamey_slug",
            monster_received="splashy_slug",
            monster_given_id=self.monster_a.instance_id,
            monster_received_id=self.monster_b.instance_id,
            timestamp=datetime.now(timezone.utc),
        )
        self.manager.global_trade_log.append(record)
        self.assertTrue(self.manager.was_traded_for_monster("flamey_slug"))
        self.assertTrue(self.manager.was_traded_for_monster("splashy_slug"))
        self.assertFalse(self.manager.was_traded_for_monster("leafy_slug"))

    def test_get_trade_history(self):
        record = TradeRecord(
            from_player="Better",
            to_player="Call",
            from_player_id=self.player_a.instance_id,
            to_player_id=self.player_b.instance_id,
            monster_given="flamey_slug",
            monster_received="splashy_slug",
            monster_given_id=self.monster_a.instance_id,
            monster_received_id=self.monster_b.instance_id,
            timestamp=datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        self.manager.global_trade_log.append(record)
        lineage = self.manager.get_trade_history()
        self.assertEqual(len(lineage), 1)
        self.assertIn("Better traded flamey_slug for splashy_slug", lineage[0])

    def test_save_and_load_log(self):
        original_record = TradeRecord(
            from_player="Better",
            to_player="Call",
            from_player_id=self.player_a.instance_id,
            to_player_id=self.player_b.instance_id,
            monster_given="flamey_slug",
            monster_received="splashy_slug",
            monster_given_id=self.monster_a.instance_id,
            monster_received_id=self.monster_b.instance_id,
            timestamp=datetime.now(timezone.utc),
        )
        self.manager.global_trade_log.append(original_record)
        saved = self.manager.save_log()

        new_manager = TradeManager()
        new_manager.event_bus = MagicMock()
        new_manager.load_log(saved)

        self.assertEqual(len(new_manager.global_trade_log), 1)
        self.assertEqual(new_manager.global_trade_log[0].from_player, "Better")

    def test_accept_trade_expired_offer(self):
        self.manager.propose_trade(self.monster_a, self.monster_b)
        offer = self.manager.pending_offers[0]

        offer.expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)

        result = self.manager.accept_trade(MagicMock(), offer.offer_id)
        self.assertEqual(result, TradeResult.EXPIRED)
        self.assertNotIn(offer, self.manager.pending_offers)

    def test_accept_trade_nonexistent_offer(self):
        fake_id = uuid4()
        result = self.manager.accept_trade(MagicMock(), fake_id)
        self.assertEqual(result, TradeResult.NOT_FOUND)

    def test_accept_trade_missing_monster(self):
        self.manager.propose_trade(self.monster_a, self.monster_b)
        offer = self.manager.pending_offers[0]

        self.player_a.party.monsters = []
        self.player_b.party.monsters = []

        result = self.manager.accept_trade(MagicMock(), offer.offer_id)
        self.assertEqual(result, TradeResult.NOT_FOUND)

    def test_get_trade_history_filtered(self):
        record = TradeRecord(
            from_player="Better",
            to_player="Call",
            from_player_id=self.player_a.instance_id,
            to_player_id=self.player_b.instance_id,
            monster_given="flamey_slug",
            monster_received="splashy_slug",
            monster_given_id=self.monster_a.instance_id,
            monster_received_id=self.monster_b.instance_id,
            timestamp=datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        self.manager.global_trade_log.append(record)
        lineage = self.manager.get_trade_history(player_name="Better")
        self.assertEqual(len(lineage), 1)
        self.assertIn("Better traded flamey_slug", lineage[0])
