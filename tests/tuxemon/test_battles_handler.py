# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.battle import Battle, BattlesHandler
from tuxemon.db import OutputBattle


class TestBattlesHandler(unittest.TestCase):
    def test_init(self):
        handler = BattlesHandler()
        self.assertEqual(handler.get_battles(), [])

    def test_add_battle(self):
        handler = BattlesHandler()
        battle = Battle(
            {
                "fighter": "player",
                "opponent": "npc",
                "outcome": OutputBattle.won,
                "steps": 10,
            }
        )
        handler.add_battle(battle)
        self.assertEqual(len(handler.get_battles()), 1)

    def test_get_battles(self):
        handler = BattlesHandler()
        battle1 = Battle(
            {
                "fighter": "player",
                "opponent": "npc",
                "outcome": OutputBattle.won,
                "steps": 10,
            }
        )
        battle2 = Battle(
            {
                "fighter": "player",
                "opponent": "npc",
                "outcome": OutputBattle.lost,
                "steps": 5,
            }
        )
        handler.add_battle(battle1)
        handler.add_battle(battle2)
        self.assertEqual(len(handler.get_battles()), 2)

    def test_clear_battles(self):
        handler = BattlesHandler()
        battle = Battle(
            {
                "fighter": "player",
                "opponent": "npc",
                "outcome": OutputBattle.won,
                "steps": 10,
            }
        )
        handler.add_battle(battle)
        handler.clear_battles()
        self.assertEqual(len(handler.get_battles()), 0)

    def test_has_fought_and_outcome(self):
        handler = BattlesHandler()
        battle = Battle(
            {
                "fighter": "player",
                "opponent": "npc",
                "outcome": OutputBattle.won,
                "steps": 10,
            }
        )
        handler.add_battle(battle)
        self.assertTrue(
            handler.has_fought_and_outcome(
                "player", OutputBattle.won.value, "npc"
            )
        )

    def test_get_last_battle_outcome(self):
        handler = BattlesHandler()
        battle1 = Battle(
            {
                "fighter": "player",
                "opponent": "npc",
                "outcome": OutputBattle.won,
                "steps": 10,
            }
        )
        battle2 = Battle(
            {
                "fighter": "player",
                "opponent": "npc",
                "outcome": OutputBattle.lost,
                "steps": 5,
            }
        )
        handler.add_battle(battle1)
        handler.add_battle(battle2)
        self.assertEqual(
            handler.get_last_battle_outcome("player", "npc"), OutputBattle.lost
        )

    def test_get_battle_outcome_stats(self):
        handler = BattlesHandler()
        battle1 = Battle(
            {
                "fighter": "player",
                "opponent": "npc",
                "outcome": OutputBattle.won,
                "steps": 10,
            }
        )
        battle2 = Battle(
            {
                "fighter": "player",
                "opponent": "npc",
                "outcome": OutputBattle.lost,
                "steps": 5,
            }
        )
        handler.add_battle(battle1)
        handler.add_battle(battle2)
        stats = handler.get_battle_outcome_stats("player")
        self.assertEqual(stats[OutputBattle.won], 1)
        self.assertEqual(stats[OutputBattle.lost], 1)
        self.assertEqual(stats[OutputBattle.draw], 0)

    def test_get_battle_outcome_summary(self):
        handler = BattlesHandler()
        battle1 = Battle(
            {
                "fighter": "player",
                "opponent": "npc",
                "outcome": OutputBattle.won,
                "steps": 10,
            }
        )
        battle2 = Battle(
            {
                "fighter": "player",
                "opponent": "npc",
                "outcome": OutputBattle.lost,
                "steps": 5,
            }
        )
        handler.add_battle(battle1)
        handler.add_battle(battle2)
        summary = handler.get_battle_outcome_summary("player")
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["won"], 1)
        self.assertEqual(summary["lost"], 1)
        self.assertEqual(summary["draw"], 0)
