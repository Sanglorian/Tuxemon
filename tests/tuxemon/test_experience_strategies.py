# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock

from tuxemon.combat.damage_tracker import DamageTracker
from tuxemon.combat.experience_strategies import (
    BondExperienceStrategy,
    DamageProportionalExperienceStrategy,
    DefaultExperienceStrategy,
    EqualExperienceStrategy,
    FeederExperienceStrategy,
    OverkillExperienceStrategy,
    StageScalingExperienceStrategy,
    SurvivorExperienceStrategy,
    TransmitterExperienceStrategy,
    calculate_experience,
    calculate_experience_base,
)
from tuxemon.db import EvolutionStage, ExperienceMethod
from tuxemon.prepare import MAX_LEVEL


class DummyMonster:
    def __init__(self, name="dummy", level=5, total_exp=1000, exp_mod=1.0):
        self.name = name
        self.level = level
        self.total_experience = total_exp
        self.experience_modifier = exp_mod
        self.held_item = None
        self.owner = None

    def get_experience_multiplier(self):
        return 1.0

    @property
    def is_fainted(self):
        return self.current_hp <= 0


class TestExperienceStrategies(unittest.TestCase):
    def setUp(self):
        self.loser = DummyMonster(
            "loser", level=5, total_exp=1000, exp_mod=1.5
        )
        self.winner = DummyMonster(
            "winner", level=5, total_exp=1000, exp_mod=1.0
        )
        self.second_attacker = DummyMonster(
            "ally", level=5, total_exp=1000, exp_mod=1.0
        )
        self.damages = DamageTracker()
        self.damages.log_damage(self.winner, self.loser, 10, 1)
        self.damages.log_damage(self.winner, self.loser, 5, 2)
        self.damages.log_damage(self.second_attacker, self.loser, 20, 3)

    def test_default_strategy(self):
        strat = DefaultExperienceStrategy()
        exp, non = strat.calculate(self.loser, self.winner, self.damages, 1.0)
        self.assertGreater(exp, 0)
        self.assertEqual(non, 0)

    def test_equal_strategy(self):
        strat = EqualExperienceStrategy()
        exp, non = strat.calculate(self.loser, self.winner, self.damages, 1.0)
        self.assertGreater(exp, 0)
        self.assertEqual(non, 0)

    def test_feeder_strategy_with_item(self):
        self.winner.held_item = MagicMock()
        self.winner.held_item.reward_method = ExperienceMethod.XP_FEEDER
        strat = FeederExperienceStrategy()
        exp, non = strat.calculate(self.loser, self.winner, self.damages, 1.0)
        self.assertGreaterEqual(exp, 0)
        self.assertEqual(non, 0)

    def test_transmitter_strategy_with_owner(self):
        owner = MagicMock()
        owner.party.alive = [self.winner]
        self.winner.owner = owner
        strat = TransmitterExperienceStrategy()
        exp, non = strat.calculate(self.loser, self.winner, self.damages, 1.0)
        self.assertGreaterEqual(exp, 0)
        self.assertGreaterEqual(non, 0)

    def test_overkill_strategy_final_blow(self):
        strat = OverkillExperienceStrategy()
        exp, non = strat.calculate(self.loser, self.winner, self.damages, 1.0)
        self.assertGreater(exp, 0)
        self.assertEqual(non, 0)

    def test_damage_proportional_strategy(self):
        strat = DamageProportionalExperienceStrategy()
        exp, non = strat.calculate(self.loser, self.winner, self.damages, 1.0)
        self.assertGreater(exp, 0)
        self.assertEqual(non, 0)

    def test_calculate_experience_default(self):
        self.winner.held_item = None
        exp, non = calculate_experience(self.loser, self.winner, self.damages)
        self.assertGreater(exp, 0)
        self.assertEqual(non, 0)

    def test_calculate_experience_max_level(self):
        self.winner.level = MAX_LEVEL
        exp, non = calculate_experience(self.loser, self.winner, self.damages)
        self.assertEqual((exp, non), (0, 0))

    def test_calculate_experience_base(self):
        base = calculate_experience_base(1000, 5, 1.5)
        expected = int((1000 // 5) * 1.5)
        self.assertEqual(base, expected)

    def test_equal_strategy_multi_attacker(self):
        strat = EqualExperienceStrategy()
        exp_winner, _ = strat.calculate(
            self.loser, self.winner, self.damages, 1.0
        )
        exp_ally, _ = strat.calculate(
            self.loser, self.second_attacker, self.damages, 1.0
        )
        self.assertGreater(exp_winner, exp_ally)

    def test_damage_proportional_strategy_multi_attacker(self):
        strat = DamageProportionalExperienceStrategy()
        exp_winner, _ = strat.calculate(
            self.loser, self.winner, self.damages, 1.0
        )
        exp_ally, _ = strat.calculate(
            self.loser, self.second_attacker, self.damages, 1.0
        )
        self.assertGreater(exp_ally, exp_winner)

    def test_transmitter_strategy_with_non_participant(self):
        non_participant = DummyMonster(
            "bench", level=5, total_exp=1000, exp_mod=1.0
        )
        owner = MagicMock()
        owner.party.alive = [
            self.winner,
            self.second_attacker,
            non_participant,
        ]
        self.winner.owner = owner
        strat = TransmitterExperienceStrategy()
        exp, non = strat.calculate(self.loser, self.winner, self.damages, 1.0)
        self.assertGreater(exp, 0)
        self.assertGreater(non, 0)

    def test_overkill_strategy_final_blow_multi_attacker(self):
        strat = OverkillExperienceStrategy()
        exp_winner, _ = strat.calculate(
            self.loser, self.winner, self.damages, 1.0
        )
        exp_ally, _ = strat.calculate(
            self.loser, self.second_attacker, self.damages, 1.0
        )
        self.assertGreater(exp_ally, exp_winner)

    def test_calculate_experience_base(self):
        base = calculate_experience_base(1000, 5, 1.5)
        expected = int((1000 // 5) * 1.5)
        self.assertEqual(base, expected)

    def test_feeder_strategy_multi_attacker_item_holder(self):
        self.winner.held_item = MagicMock()
        self.winner.held_item.reward_method = ExperienceMethod.XP_FEEDER
        self.second_attacker.held_item = None
        strat = FeederExperienceStrategy()
        exp_winner, _ = strat.calculate(
            self.loser, self.winner, self.damages, 1.0
        )
        exp_ally, _ = strat.calculate(
            self.loser, self.second_attacker, self.damages, 1.0
        )
        self.assertGreaterEqual(exp_winner, exp_ally)

    def test_feeder_strategy_multi_attacker_no_item(self):
        self.winner.held_item = None
        self.second_attacker.held_item = None
        strat = FeederExperienceStrategy()
        exp_winner, _ = strat.calculate(
            self.loser, self.winner, self.damages, 1.0
        )
        exp_ally, _ = strat.calculate(
            self.loser, self.second_attacker, self.damages, 1.0
        )
        self.assertGreater(exp_winner, 0)
        self.assertGreater(exp_ally, 0)
        self.assertNotEqual(exp_winner, 0)
        self.assertNotEqual(exp_ally, 0)

    def test_bond_experience_strategy(self):
        self.winner.bond_handler = MagicMock(bond=50)
        strat = BondExperienceStrategy()
        exp, non = strat.calculate(self.loser, self.winner, self.damages, 1.0)
        self.assertGreater(exp, 0)
        self.assertEqual(non, 0)

    def test_bond_experience_strategy_scaling(self):
        self.winner.bond_handler = MagicMock(bond=100)
        strat = BondExperienceStrategy()
        exp_high, _ = strat.calculate(
            self.loser, self.winner, self.damages, 1.0
        )
        self.winner.bond_handler.bond = 1
        exp_low, _ = strat.calculate(
            self.loser, self.winner, self.damages, 1.0
        )
        self.assertGreater(exp_high, exp_low)
        self.assertEqual(_, 0)

    def test_stage_scaling_experience_strategy(self):
        self.loser.stage = EvolutionStage.stage1
        strat = StageScalingExperienceStrategy()
        exp_evolved, _ = strat.calculate(
            self.loser, self.winner, self.damages, 1.0
        )

        self.loser.stage = EvolutionStage.basic
        exp_basic, _ = strat.calculate(
            self.loser, self.winner, self.damages, 1.0
        )

        self.assertGreater(exp_evolved, exp_basic)
        self.assertEqual(_, 0)

    def test_survivor_experience_strategy(self):
        ally = DummyMonster("ally", level=5, total_exp=1000, exp_mod=1.0)
        owner = MagicMock()
        owner.party.alive = [self.winner, ally]
        self.winner.owner = owner

        ally.current_hp = 0
        self.winner.current_hp = 10

        strat = SurvivorExperienceStrategy()
        exp, non = strat.calculate(self.loser, self.winner, self.damages, 1.0)

        self.assertGreater(exp, 0)
        self.assertEqual(non, 0)
