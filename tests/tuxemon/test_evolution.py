# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock, PropertyMock, patch

from tuxemon.db import (
    Acquisition,
    BondComparison,
    Comparison,
    GenderType,
    LearningMethod,
    MonsterEvolutionItemModel,
    PartyConditionsModel,
    SeenStatus,
    StatsComparison,
    StatType,
)
from tuxemon.game_variables import GameVariablesManager
from tuxemon.monster import Monster
from tuxemon.monster_dir.evolution import Evolution
from tuxemon.npc import PartyHandler
from tuxemon.player import Player
from tuxemon.session import local_session
from tuxemon.technique.technique import Technique


def mockPlayer(self) -> None:
    self.name = "Jeff"
    self._variables = GameVariablesManager()
    member1 = Monster()
    member1.slug = "nut"
    member2 = Monster()
    member2.slug = "rockitten"
    tech = MagicMock(spec=Technique, slug="ram")
    member1.moves.moves = [tech]
    self.party = PartyHandler(MagicMock, self)
    self.party._monsters = [member1, member2]
    self.tuxepedia = MagicMock()


class TestEvolution(unittest.TestCase):
    def setUp(self):
        self.mon = Monster()
        with patch.object(Player, "__init__", mockPlayer):
            local_session.set_player(Player())
            self.player = local_session.player
            self.mon.set_owner(self.player)
        self.evo = Evolution(self.mon)

    def test_evolve_monster_success(self):
        new_mon = Monster()
        new_mon.slug = "rockat"
        move = MagicMock()
        move.learning_method = LearningMethod.EVOLUTION
        move.technique = "SpecialBeam"
        new_mon.moves.moveset = [move]
        self.evo.is_eligible_for_evolution = lambda: True
        new_mon.transfer_properties_from = MagicMock()
        new_mon.moves.learn_by_method = MagicMock()
        self.player.party.replace_monster = MagicMock(return_value=True)
        self.player.tuxepedia.add_entry = MagicMock()
        self.evo.evolve_monster(new_mon)
        new_mon.transfer_properties_from.assert_called_with(self.mon)
        new_mon.moves.learn_by_method.assert_called_with(
            new_mon, "SpecialBeam", LearningMethod.EVOLUTION
        )
        self.player.party.replace_monster.assert_called_with(self.mon, new_mon)
        self.player.tuxepedia.add_entry.assert_called_with(
            "rockat", SeenStatus.caught
        )

    def test_evolve_monster_not_eligible(self):
        new_mon = Monster()
        self.evo.is_eligible_for_evolution = lambda: False
        new_mon.transfer_properties_from = MagicMock()
        self.evo.evolve_monster(new_mon)
        new_mon.transfer_properties_from.assert_not_called()

    def test_evolve_monster_replace_fails(self):
        new_mon = Monster()
        new_mon.slug = "rockat"
        self.evo.is_eligible_for_evolution = lambda: True
        new_mon.transfer_properties_from = MagicMock()
        self.player.party.replace_monster = MagicMock(return_value=False)
        self.player.tuxepedia = MagicMock()
        self.evo.evolve_monster(new_mon)
        self.assertFalse(self.player.tuxepedia.add_entry.called)

    def test_no_owner(self):
        self.mon.set_owner(None)
        evo = MonsterEvolutionItemModel(monster_slug="rockat")
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_level_too_low(self):
        self.mon.set_level(10)
        evo = MonsterEvolutionItemModel(monster_slug="rockat", at_level=20)
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_level_meets_requirement(self):
        self.mon.set_level(20)
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
        self.mon.set_level(20)
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
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat",
            party_conditions=PartyConditionsModel(monster_slugs={"nut": 1}),
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_party_match_double(self):
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat",
            party_conditions=PartyConditionsModel(
                monster_slugs={"nut": 1, "rockitten": 1}
            ),
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_party_mismatch(self):
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat",
            party_conditions=PartyConditionsModel(
                monster_slugs={"agnidon": 1}
            ),
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_taste_match(self):
        self.mon.taste_cold = "flakey"
        evo_cold = MonsterEvolutionItemModel(
            monster_slug="rockat", tastes={"cold": "flakey"}
        )
        context = {"map_inside": True}
        self.assertTrue(
            self.mon.evolution_handler.can_evolve(evo_cold, context)
        )

        self.mon.taste_warm = "peppy"
        evo_warm = MonsterEvolutionItemModel(
            monster_slug="rockat", tastes={"warm": "peppy"}
        )
        context = {"map_inside": True}
        self.assertTrue(
            self.mon.evolution_handler.can_evolve(evo_warm, context)
        )

    def test_taste_mismatch(self):
        self.mon.taste_cold = "mild"
        evo_cold = MonsterEvolutionItemModel(
            monster_slug="rockat", tastes={"cold": "flakey"}
        )
        context = {"map_inside": True}
        self.assertFalse(
            self.mon.evolution_handler.can_evolve(evo_cold, context)
        )

        self.mon.taste_warm = "peppy"
        evo_warm = MonsterEvolutionItemModel(
            monster_slug="rockat", tastes={"warm": "salty"}
        )
        context = {"map_inside": True}
        self.assertFalse(
            self.mon.evolution_handler.can_evolve(evo_warm, context)
        )

    def test_stats_match(self):
        self.mon.base_stats.hp = 30
        self.mon.base_stats.melee = 20
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat",
            stats=StatsComparison(
                stat_type=StatType.hp,
                comparison=Comparison.greater_or_equal,
                target_stat=StatType.melee,
            ),
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_stats_mismatch(self):
        self.mon.base_stats.speed = 5
        self.mon.base_stats.armour = 10
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat",
            stats=StatsComparison(
                stat_type=StatType.speed,
                comparison=Comparison.greater_or_equal,
                target_stat=StatType.armour,
            ),
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_variables_match(self):
        self.player.game_variables.set("var", "val")
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", variables=[{"var": "val"}]
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_variables_mismatch(self):
        self.player.game_variables.set("var", "other_val")
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", variables=[{"var": "val"}]
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_variables_double_match(self):
        self.player.game_variables.set("var1", "val")
        self.player.game_variables.set("var2", "val")
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", variables=[{"var1": "val"}, {"var2": "val"}]
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_variables_double_mismatch(self):
        self.player.game_variables.set("var1", "val")
        self.player.game_variables.set("var2", "val")
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
        self.mon.bond_handler.bond = 10
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat",
            bond=BondComparison(
                comparison=Comparison.greater_or_equal, value=10
            ),
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_bond_mismatch(self):
        self.mon.bond_handler.bond = 5
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat",
            bond=BondComparison(
                comparison=Comparison.greater_or_equal, value=10
            ),
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_item_match(self):
        evo = MonsterEvolutionItemModel(
            monster_slug="botbot", item={"booster_tech": 1.0}
        )
        context = {"map_inside": True, "use_item": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_item_mismatch(self):
        evo = MonsterEvolutionItemModel(
            monster_slug="botbot", item={"booster_tech": 1.0}
        )
        context = {"map_inside": True, "use_item": False}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_element_match(self):
        element = MagicMock(slug="metal")
        self.mon.types.set_types([element])
        evo = MonsterEvolutionItemModel(monster_slug="botbot", element="metal")
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_element_mismatch(self):
        element = MagicMock(slug="metal")
        self.mon.types.set_types([element])
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

    @patch("random.random", return_value=0.05)
    def test_probability_success(self, mock_random):
        self.mon.set_level(20)
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", at_level=20, probability=0.1  # 10% chance
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    @patch("random.random", return_value=0.15)
    def test_probability_failure(self, mock_random):
        self.mon.set_level(20)
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", at_level=20, probability=0.1  # 10% chance
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    @patch("random.random", return_value=0.05)
    def test_evolution_probability_only_success(self, mock_random):
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", probability=0.1  # 10% chance
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    @patch("random.random", return_value=0.15)
    def test_evolution_probability_only_failure(self, mock_random):
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", probability=0.1  # 10% chance
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_evolution_with_correct_held_item(self):
        item = MagicMock(slug="potion")
        self.mon.item_handler.set_item(item)

        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", held_item="potion"
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_evolution_with_wrong_held_item(self):
        item = MagicMock(slug="tea")
        self.mon.item_handler.set_item(item)

        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", held_item="potion"
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_evolution_with_no_item_held(self):
        evo = MonsterEvolutionItemModel(
            monster_slug="rockat", held_item="potion"
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_can_evolve_party_alignment_matches(self):
        with patch.object(
            type(self.player.party), "alignment", new_callable=PropertyMock
        ) as mock_alignment:
            mock_alignment.return_value = "fire"
            evolution_item = MonsterEvolutionItemModel(
                monster_slug="nut",
                party_conditions=PartyConditionsModel(alignment="fire"),
            )
            context = {"map_inside": True}
            result = self.mon.evolution_handler.can_evolve(
                evolution_item, context
            )
            self.assertTrue(result)

    def test_can_evolve_party_alignment_mismatch(self):
        with patch.object(
            type(self.player.party), "alignment", new_callable=PropertyMock
        ) as mock_alignment:
            mock_alignment.return_value = "water"
            evolution_item = MonsterEvolutionItemModel(
                monster_slug="nut",
                party_conditions=PartyConditionsModel(alignment="fire"),
            )
            context = {"map_inside": True}
            result = self.mon.evolution_handler.can_evolve(
                evolution_item, context
            )
            self.assertFalse(result)

    def test_can_evolve_gender_match(self):
        for mon in self.player.party._monsters:
            mon.gender = GenderType.male

        evo = MonsterEvolutionItemModel(
            monster_slug="rockat",
            party_conditions=PartyConditionsModel(
                genders={GenderType.male: 1}
            ),
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_can_evolve_gender_mismatch(self):
        for mon in self.player.party._monsters:
            mon.gender = GenderType.female

        evo = MonsterEvolutionItemModel(
            monster_slug="rockat",
            party_conditions=PartyConditionsModel(
                genders={GenderType.male: 1}
            ),
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_can_evolve_type_match(self):
        element = MagicMock(slug="earth")
        for mon in self.player.party._monsters:
            mon.types.set_types([element])

        evo = MonsterEvolutionItemModel(
            monster_slug="rockat",
            party_conditions=PartyConditionsModel(monster_types={"earth": 1}),
        )
        context = {"map_inside": True}
        self.assertTrue(self.mon.evolution_handler.can_evolve(evo, context))

    def test_can_evolve_type_mismatch(self):
        element = MagicMock(slug="water")
        for mon in self.player.party._monsters:
            mon.types.set_types([element])

        evo = MonsterEvolutionItemModel(
            monster_slug="rockat",
            party_conditions=PartyConditionsModel(monster_types={"fire": 1}),
        )
        context = {"map_inside": True}
        self.assertFalse(self.mon.evolution_handler.can_evolve(evo, context))

    def test_returns_valid_evolutions(self):
        item = MagicMock()
        item.slug = "stone"
        evo_model_valid = MagicMock(spec=MonsterEvolutionItemModel)
        evo_model_valid.item = {"stone": 1.0}
        evo_model_valid.monster_slug = "rockat"
        evo_model_invalid = MagicMock(spec=MonsterEvolutionItemModel)
        evo_model_invalid.item = {"other_item": 1.0}
        evo_model_invalid.monster_slug = "nut"
        self.mon.evolutions = [evo_model_valid, evo_model_invalid]
        self.evo.can_evolve = MagicMock(return_value=True)
        context = {"use_item": True}
        result = self.evo.get_possible_item_evolutions(item, context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0].monster_slug, "rockat")
        self.assertEqual(result[0][1], 1.0)

    def test_filters_out_weight_zero(self):
        item = MagicMock()
        item.slug = "stone"
        evo_model = MagicMock(spec=MonsterEvolutionItemModel)
        evo_model.item = {"stone": 0.0}
        evo_model.monster_slug = "rockat"
        self.mon.evolutions = [evo_model]
        self.evo.can_evolve = MagicMock(return_value=True)
        context = {"use_item": True}
        result = self.evo.get_possible_item_evolutions(item, context)
        self.assertEqual(result, [])

    def test_filters_out_ineligible(self):
        item = MagicMock()
        item.slug = "stone"
        evo_model = MagicMock(spec=MonsterEvolutionItemModel)
        evo_model.item = {"stone": 1.0}
        evo_model.monster_slug = "rockat"
        self.mon.evolutions = [evo_model]
        self.evo.can_evolve = MagicMock(return_value=False)
        context = {"use_item": True}
        result = self.evo.get_possible_item_evolutions(item, context)
        self.assertEqual(result, [])

    def test_single_evolution_returns_model(self):
        evo_model = MagicMock(spec=MonsterEvolutionItemModel)
        possible_evolutions = [(evo_model, 1.0)]
        result = self.evo.choose_evolution_model(possible_evolutions)
        self.assertIs(result, evo_model)

    @patch("random.choices")
    def test_multiple_evolutions_uses_random_choices(self, mock_choices):
        evo_model1 = MagicMock(spec=MonsterEvolutionItemModel)
        evo_model2 = MagicMock(spec=MonsterEvolutionItemModel)
        possible_evolutions = [(evo_model1, 0.5), (evo_model2, 0.5)]
        mock_choices.return_value = [evo_model2]
        result = self.evo.choose_evolution_model(possible_evolutions)
        self.assertIs(result, evo_model2)
        mock_choices.assert_called_once()
        args, kwargs = mock_choices.call_args
        self.assertIn(evo_model1, args[0])
        self.assertIn(evo_model2, args[0])
        self.assertEqual(list(kwargs["weights"]), [0.5, 0.5])
        self.assertEqual(kwargs["k"], 1)

    def test_empty_evolutions_raises_error(self):
        with self.assertRaises(ValueError):
            self.evo.choose_evolution_model([])

    def test_is_valid_evolution_target_true_for_direct(self):
        self.evo.has_evolution_to = MagicMock(return_value=True)
        self.evo.has_history_to = MagicMock(return_value=False)
        result = self.evo.is_valid_evolution_target("slug123")
        self.assertTrue(result)

    def test_is_valid_evolution_target_true_for_history(self):
        self.evo.has_evolution_to = MagicMock(return_value=False)
        self.evo.has_history_to = MagicMock(return_value=True)
        result = self.evo.is_valid_evolution_target("slug123")
        self.assertTrue(result)

    def test_is_valid_evolution_target_false(self):
        self.evo.has_evolution_to = MagicMock(return_value=False)
        self.evo.has_history_to = MagicMock(return_value=False)
        result = self.evo.is_valid_evolution_target("slug123")
        self.assertFalse(result)

    def test_confirm_pending_evolution_calls_registry_and_resets_flags(self):
        registry = MagicMock()
        self.mon.instance_id = "iid123"
        self.mon.experience_handler.reset_status_flags = MagicMock()
        self.evo.confirm_pending_evolution(registry, "slug123")
        registry.clear_missed.assert_called_once_with("iid123", "slug123")
        registry.clear_pending.assert_called_once_with("iid123")
        self.mon.experience_handler.reset_status_flags.assert_called_once()

    def test_deny_pending_evolution_calls_registry_and_resets_flags(self):
        registry = MagicMock()
        self.mon.instance_id = "iid123"
        self.mon.set_level(10)
        self.mon.experience_handler.reset_status_flags = MagicMock()
        self.evo.deny_pending_evolution(registry, "slug123")
        registry.log_missed.assert_called_once_with("iid123", "slug123", 10)
        registry.clear_pending.assert_called_once_with("iid123")
        self.mon.experience_handler.reset_status_flags.assert_called_once()
