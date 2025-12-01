# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock, PropertyMock

from tuxemon.combat.combat_context import CombatType
from tuxemon.combat.damage_tracker import DamageTracker
from tuxemon.combat.experience_strategies import calculate_experience_base
from tuxemon.combat.reward_system import (
    RewardSystem,
    TrainerRewardCalculator,
    calculate_experience,
    calculate_money,
    calculate_tps,
)
from tuxemon.db import Acquisition, ExperienceMethod
from tuxemon.monster import Monster
from tuxemon.monster_dir.stats import BasicStats
from tuxemon.monster_dir.status import MonsterStatusHandler
from tuxemon.npc import NPC
from tuxemon.prepare import MAX_LEVEL


class DummyItem:
    def __init__(self, method: ExperienceMethod, multiplier: float):
        self.reward_method = method
        self.money_multiplier = multiplier


class TestRewardSystem(unittest.TestCase):
    def setUp(self):
        self.loser = Monster()
        self.loser.name = "pairagrin"
        self.loser.set_level(5)
        self.loser.money_modifier = 1.0
        self.loser.status = MagicMock(spec=MonsterStatusHandler)
        self.loser.current_hp = 0
        self.loser.stage = "basic"
        self.loser.moves = MagicMock()
        self.loser.set_total_experience(1000)
        self.loser.set_experience_modifier(1.5)

        self.winner = Monster()
        self.winner.name = "rockitten"
        self.winner.set_level(5)
        self.winner.moves = MagicMock()
        self.winner.current_hp = 50
        self.winner.stage = "basic"
        self.winner.acquisition = Acquisition.UNKNOWN
        self.winner.owner = MagicMock(spec=NPC)
        self.winner.owner.is_player = True
        self.winner.owner.monsters = [self.winner]
        self.winner.owner.party = MagicMock()
        self.winner.owner.party.alive = [self.winner]
        self.winner.base_stats = BasicStats()

        self.session = MagicMock()
        self.combat_type = CombatType.TRAINER

        self.damage_tracker = DamageTracker()
        self.damage_tracker.log_damage(self.winner, self.loser, 10, 1)

        self.calculator = TrainerRewardCalculator(self.damage_tracker)
        self.reward_system = RewardSystem(
            self.session, self.combat_type, self.calculator
        )

    def test_reward_system_winner(self):
        reward_system = RewardSystem(
            self.session, self.combat_type, self.calculator
        )
        rewards = reward_system.award_rewards(self.loser)

        self.assertEqual(len(rewards.winners), 1)
        self.assertEqual(rewards.winners[0].winner, self.winner)

    def test_reward_system_money(self):
        reward_system = RewardSystem(
            self.session, self.combat_type, self.calculator
        )
        rewards = reward_system.award_rewards(self.loser)

        awarded_money = calculate_money(self.loser, self.winner)
        self.assertEqual(rewards.winners[0].money, awarded_money)
        self.assertEqual(rewards.prize, awarded_money)

    def test_reward_system_experience(self):
        reward_system = RewardSystem(
            self.session, self.combat_type, self.calculator
        )
        rewards = reward_system.award_rewards(self.loser)

        awarded_exp, _ = calculate_experience(
            self.loser, self.winner, self.damage_tracker
        )
        self.assertEqual(rewards.winners[0].experience, awarded_exp)

    def test_reward_system_update(self):
        reward_system = RewardSystem(
            self.session, self.combat_type, self.calculator
        )
        rewards = reward_system.award_rewards(self.loser)
        self.assertTrue(rewards.update)

    def test_calculate_money_with_multiplier_item(self):
        type(self.loser).held_item = PropertyMock(return_value=None)
        type(self.winner).held_item = PropertyMock(
            return_value=DummyItem(ExperienceMethod.DEFAULT, 2.0)
        )

        money = calculate_money(self.loser, self.winner)
        expected_money = calculate_money(self.loser, self.winner)
        self.assertEqual(money, expected_money)

    def test_calculate_money_with_fractional_multiplier(self):
        type(self.loser).held_item = PropertyMock(return_value=None)
        type(self.winner).held_item = PropertyMock(
            return_value=DummyItem(ExperienceMethod.DEFAULT, 0.5)
        )

        money = calculate_money(self.loser, self.winner)
        expected_money = calculate_money(self.loser, self.winner)
        self.assertEqual(money, expected_money)

    def test_calculate_experience_default_method(self):
        type(self.winner).held_item = PropertyMock(return_value=None)

        experience = calculate_experience(
            self.loser, self.winner, self.damage_tracker
        )
        expected_experience = int(
            (self.loser.total_experience // (self.loser.level))
            * self.loser.experience_modifier
        )
        self.assertEqual(experience[0], expected_experience)

    def test_calculate_experience_with_transmitter(self):
        mock_monsters = [
            MagicMock(
                spec=Monster,
                name="participant1",
                current_hp=50,
                status=[],
                stage="basic",
            ),
            MagicMock(
                spec=Monster,
                name="participant2",
                current_hp=50,
                status=[],
                stage="basic",
            ),
            MagicMock(
                spec=Monster,
                name="non_participant",
                current_hp=50,
                status=[],
                stage="basic",
            ),
        ]

        self.winner.item_handler = MagicMock()
        type(self.winner).held_item = PropertyMock(
            return_value=DummyItem(ExperienceMethod.XP_TRANSMITTER, 2.0)
        )

        experience = calculate_experience(
            self.loser, self.winner, self.damage_tracker
        )

        total_exp = calculate_experience_base(
            self.loser.total_experience,
            self.loser.level,
            self.loser.experience_modifier,
        )
        participants = self.damage_tracker.get_attackers(self.loser)
        participant_exp = total_exp // 2 // len(participants)

        self.assertEqual(experience[0], participant_exp)

    def test_calculate_experience_base(self):
        experience = calculate_experience_base(
            self.loser.total_experience,
            self.loser.level,
            self.loser.experience_modifier,
        )
        expected_experience = int(
            (self.loser.total_experience // (self.loser.level))
            * self.loser.experience_modifier
        )
        self.assertEqual(experience, expected_experience)

    def test_award_rewards_distribution(self):
        mock_monsters = [
            MagicMock(
                spec=Monster,
                give_experience=MagicMock(),
                moves=MagicMock(),
                level=5,
                status=MonsterStatusHandler(),
                current_hp=50,
                is_fainted=False,
                stage="basic",
            )
            for _ in range(3)
        ]

        self.winner.owner.monsters = mock_monsters
        self.winner.owner.party = MagicMock()
        self.winner.owner.party.alive = mock_monsters

        reward_system = RewardSystem(
            self.session, self.combat_type, self.calculator
        )
        rewards = reward_system.award_rewards(self.loser)

        self.assertEqual(len(rewards.winners), 1)
        self.assertEqual(rewards.winners[0].winner, self.winner)

        awarded_money = calculate_money(self.loser, self.winner)
        awarded_exp, _ = calculate_experience(
            self.loser, self.winner, self.damage_tracker
        )
        self.assertEqual(rewards.winners[0].money, awarded_money)
        self.assertEqual(rewards.winners[0].experience, awarded_exp)

        for monster in mock_monsters:
            monster.give_experience.assert_called()

    def test_award_rewards_no_winners(self):
        empty_tracker = DamageTracker()
        calculator = TrainerRewardCalculator(empty_tracker)
        reward_system = RewardSystem(
            self.session, self.combat_type, calculator
        )
        rewards = reward_system.award_rewards(self.loser)

        self.assertEqual(len(rewards.winners), 0)
        self.assertEqual(rewards.prize, 0)
        self.assertFalse(rewards.update)
        self.assertEqual(rewards.moves, [])
        self.assertEqual(rewards.messages, [])

    def test_award_rewards_no_new_moves(self):
        self.winner.moves.update_moves.return_value = []
        reward_system = RewardSystem(
            self.session, self.combat_type, self.calculator
        )
        rewards = reward_system.award_rewards(self.loser)

        self.assertEqual(rewards.moves, [])

    def test_award_rewards_multiple_move_updates(self):
        self.winner.moves.update_moves.return_value = ["Fireball"]
        second_winner = Monster()
        second_winner.name = "rockitten"
        second_winner.stage = "basic"
        second_winner.set_level(5)
        second_winner.moves = MagicMock()
        second_winner.moves.update_moves.return_value = ["Ram"]
        second_winner.acquisition = Acquisition.UNKNOWN
        second_winner.owner = self.winner.owner
        second_winner.current_hp = 50
        second_winner.item_handler = MagicMock(
            held_item=MagicMock(slug="default")
        )

        self.damage_tracker.log_damage(second_winner, self.loser, 5, 1)

        reward_system = RewardSystem(
            self.session, self.combat_type, self.calculator
        )
        rewards = reward_system.award_rewards(self.loser)

        self.assertIn("Fireball", rewards.moves)
        self.assertIn("Ram", rewards.moves)
        self.assertEqual(len(rewards.moves), 2)

    def test_award_rewards_with_held_item_modifier(self):
        type(self.winner).held_item = PropertyMock(
            return_value=DummyItem(ExperienceMethod.XP_TRANSMITTER, 2.0)
        )
        reward_system = RewardSystem(
            self.session, self.combat_type, self.calculator
        )
        rewards = reward_system.award_rewards(self.loser)

        self.assertGreater(rewards.winners[0].experience, 0)

    def test_award_rewards_non_player_monster(self):
        self.winner.owner.is_player = False
        reward_system = RewardSystem(
            self.session, self.combat_type, self.calculator
        )
        rewards = reward_system.award_rewards(self.loser)

        self.assertEqual(rewards.prize, 0)
        self.assertEqual(rewards.messages, [])
        self.assertFalse(rewards.update)

    def test_calculate_tps_awards_points(self):
        loser = Monster()
        loser.base_stats = BasicStats(hp=10, melee=20)
        winner = Monster()
        winner.name = "rockitten"
        winner.base_stats = BasicStats(hp=5, melee=10)
        winner.give_tps = MagicMock()

        awarded = calculate_tps(winner, loser, tp_gain=3)

        self.assertIn(("hp", 3), awarded)
        self.assertIn(("melee", 3), awarded)
        winner.give_tps.assert_any_call("hp", 3)
        winner.give_tps.assert_any_call("melee", 3)

    def test_calculate_tps_no_award_when_winner_higher(self):
        loser = Monster()
        loser.base_stats = BasicStats(hp=5, melee=5)
        winner = Monster()
        winner.base_stats = BasicStats(hp=10, melee=10)
        winner.give_tps = MagicMock()

        awarded = calculate_tps(winner, loser)

        self.assertEqual(awarded, [])
        winner.give_tps.assert_not_called()

    def test_apply_penalties_sets_hp_and_bond(self):
        monster = Monster()
        monster.current_hp = 50
        monster.get_owner = MagicMock()
        owner = monster.get_owner.return_value
        owner.bag.find_item.return_value = True
        monster.bond_handler = MagicMock()

        reward_system = RewardSystem(
            self.session, self.combat_type, self.calculator
        )
        reward_system.apply_penalties(monster)

        self.assertEqual(monster.current_hp, 0)
        monster.bond_handler.apply_bond_modifier.assert_called_with("fainted")

    def test_calculate_experience_max_level_returns_zero(self):
        self.winner.set_level(MAX_LEVEL)
        exp = calculate_experience(
            self.loser, self.winner, self.damage_tracker
        )
        self.assertEqual(exp, (0, 0))
