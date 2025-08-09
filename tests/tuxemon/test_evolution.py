# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock, patch

from tuxemon.db import Acquisition, MonsterEvolutionItemModel
from tuxemon.element import Element
from tuxemon.monster import Monster
from tuxemon.npc import PartyHandler
from tuxemon.player import Player
from tuxemon.session import local_session
from tuxemon.technique.technique import Technique


def mockPlayer(self) -> None:
    self.name = "Jeff"
    self.game_variables = {}
    member1 = Monster()
    member1.slug = "nut"
    member2 = Monster()
    member2.slug = "rockitten"
    tech = MagicMock(spec=Technique, slug="ram")
    member1.moves.moves = [tech]
    self.party = PartyHandler(MagicMock, self)
    self.party._monsters = [member1, member2]


class TestCanEvolve(unittest.TestCase):
    def setUp(self):
        self.mon = Monster()
        with patch.object(Player, "__init__", mockPlayer):
            local_session.set_player(Player())
            self.player = local_session.player
            self.mon.set_owner(self.player)

    def test_no_owner(self):
        self.mon.set_owner(None)
        evo = MonsterEvolutionItemModel(monster_slug="rockat")
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_level_too_low(self):
        self.mon.level = 10
        evo = MonsterEvolutionItemModel(monster_slug="rockat", at_level=20)
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_level_meets_requirement(self):
        self.mon.level = 20
        evo = MonsterEvolutionItemModel(monster_slug="rockat", at_level=20)
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_gender_mismatch(self):
        self.mon.gender = "male"
        evo = MonsterEvolutionItemModel(monster_slug="rockat", gender="female")
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_gender_match(self):
        self.mon.gender = "male"
        evo = MonsterEvolutionItemModel(monster_slug="rockat", gender="male")
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_inside_mismatch(self):
        evo = MonsterEvolutionItemModel(monster_slug="rockat", inside=True)
        context = {"map_inside": False}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_inside_match(self):
        evo = MonsterEvolutionItemModel(monster_slug="rockat", inside=True)
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_all_conditions_met(self):
        self.mon.level = 20
        self.mon.gender = "male"
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", at_level=20, gender="male", inside=True
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_same_monster_slug(self):
        self.mon.slug = "rockat"
        evo = MonsterEvolutionItemModel(monster_slug="rockat")
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_tech_match(self):
        evo = MonsterEvolutionItemModel(monster_slug="rockat", tech="ram")
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_traded_match(self):
        self.mon.set_acquisition(Acquisition.TRADED)
        evo = MonsterEvolutionItemModel(monster_slug="rockat")
        evo.acquisition = Acquisition.TRADED
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_traded_mismatch(self):
        self.mon.set_acquisition(Acquisition.GIFTED)
        evo = MonsterEvolutionItemModel(monster_slug="rockat")
        evo.acquisition = Acquisition.TRADED
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_party_match(self):
        evo = MonsterEvolutionItemModel(monster_slug="rockat", party=["nut"])
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_party_match_double(self):
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", party=["nut", "rockitten"]
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_party_mismatch(self):
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", party=["agnidon"]
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_taste_cold_match(self):
        self.mon.taste_cold = "flakey"
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", taste_cold="flakey"
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_taste_cold_mismatch(self):
        self.mon.taste_cold = "mild"
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", taste_cold="flakey"
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_taste_warm_match(self):
        self.mon.taste_warm = "peppy"
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", taste_warm="peppy"
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_taste_warm_mismatch(self):
        self.mon.taste_warm = "peppy"
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", taste_warm="salty"
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_stats_match(self):
        self.mon.base_stats.hp = 30
        self.mon.base_stats.melee = 20
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", stats="hp:greater_or_equal:melee"
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_stats_mismatch(self):
        self.mon.base_stats.speed = 5
        self.mon.base_stats.armour = 10
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", stats="speed:greater_or_equal:armour"
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_variables_match(self):
        self.player.game_variables["var"] = "val"
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", variables=[{"var": "val"}]
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_variables_mismatch(self):
        self.player.game_variables["var"] = "other_val"
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", variables=[{"var": "val"}]
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_variables_double_match(self):
        self.player.game_variables["var1"] = "val"
        self.player.game_variables["var2"] = "val"
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", variables=[{"var1": "val"}, {"var2": "val"}]
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_variables_double_mismatch(self):
        self.player.game_variables["var1"] = "val"
        self.player.game_variables["var2"] = "val"
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat",
            variables=[{"var1": "val"}, {"var2": "other_val"}],
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_steps_match(self):
        self.mon.steps = 10
        evo = MonsterEvolutionItemModel(monster_slug="rockat", steps=10)
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_steps_mismatch(self):
        self.mon.steps = 5
        evo = MonsterEvolutionItemModel(monster_slug="rockat", steps=10)
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_bond_match(self):
        self.mon.bond = 10
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", bond="greater_or_equal:10"
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_bond_mismatch(self):
        self.mon.bond = 5
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", bond="greater_or_equal:10"
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_item_match(self):
        evo = MonsterEvolutionItemModel(
            monster_slug="botbot", item="booster_tech"
        )
        context = {"map_inside": True, "use_item": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_item_mismatch(self):
        evo = MonsterEvolutionItemModel(
            monster_slug="botbot", item="booster_tech"
        )
        context = {"map_inside": True, "use_item": False}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_element_match(self):
        self.mon.types.set_types([Element("metal")])
        evo = MonsterEvolutionItemModel(monster_slug="botbot", element="metal")
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_element_mismatch(self):
        self.mon.types.set_types([Element("metal")])
        evo = MonsterEvolutionItemModel(monster_slug="botbot", element="water")
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_moves_match(self):
        tech = MagicMock(spec=Technique, slug="ram")
        self.mon.moves.moves = [tech]
        evo = MonsterEvolutionItemModel(monster_slug="rockat", moves=["ram"])
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_moves_mismatch(self):
        tech = MagicMock(spec=Technique, slug="ram")
        self.mon.moves.moves = [tech]
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", moves=["strike"]
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))
