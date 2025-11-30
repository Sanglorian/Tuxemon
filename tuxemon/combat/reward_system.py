# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from tuxemon.combat.combat_context import CombatType
from tuxemon.combat.utils import alive_party
from tuxemon.db import ExperienceMethod
from tuxemon.locale import T
from tuxemon.monster_dir.stats import BasicStats
from tuxemon.prepare import DEFAULT_TP_GAIN, MAX_LEVEL

if TYPE_CHECKING:
    from tuxemon.combat.damage_tracker import DamageTracker
    from tuxemon.monster import Monster
    from tuxemon.session import Session
    from tuxemon.technique.technique import Technique

logger = logging.getLogger(__name__)


@dataclass
class RewardDataEntry:
    winner: Monster
    money: int
    experience: int
    levels_gained: int = 0


@dataclass
class RewardData:
    winners: list[RewardDataEntry]
    messages: list[str]
    moves: list[Technique]
    update: bool
    prize: int


class RewardSystem:
    def __init__(
        self,
        session: Session,
        combat_type: CombatType,
        calculator: RewardCalculator,
    ) -> None:
        self.session = session
        self.combat_type = combat_type
        self.calculator = calculator

    def apply_penalties(self, monster: Monster) -> None:
        """Applies defeat-related penalties to the specified monster."""
        monster.current_hp = 0
        owner = monster.get_owner()
        if owner.bag.find_item("friendship_scroll"):
            monster.bond_handler.apply_bond_modifier("fainted")

    def award_rewards(
        self, loser: Monster, winners: Optional[set[Monster]] = None
    ) -> RewardData:
        """Calculate and distribute rewards to winners."""
        if winners is None:
            winners = self.calculator.get_attackers(loser)

        rewards_data = RewardData([], [], [], False, 0)

        if not winners:
            return rewards_data

        # Handle non-participants
        self.calculator.calculate_non_participant_rewards(loser, winners)

        # Handle winners
        for winner in winners:
            if winner.owner and winner.owner.is_player:
                entry = self.calculator.calculate_winner_entry(loser, winner)
                rewards_data.winners.append(entry)

                self.calculator.update_moves_and_messages(
                    winner, entry, rewards_data
                )

                if self.combat_type == CombatType.TRAINER:
                    rewards_data.prize += entry.money

                rewards_data.update = True

        return rewards_data


class RewardCalculator:
    def __init__(self, damage_map: DamageTracker):
        self.damage_map = damage_map

    def get_attackers(self, loser: Monster) -> set[Monster]:
        return self.damage_map.get_attackers(loser)

    def calculate_non_participant_rewards(
        self, loser: Monster, winners: set[Monster]
    ) -> None:
        """Distribute experience to non-participating monsters in the party."""
        first_winner = next(iter(winners))
        _, awarded_exp = calculate_experience(
            loser, first_winner, self.damage_map
        )

        owner = first_winner.owner
        if owner:
            all_monsters = set(alive_party(owner))
            non_participants = all_monsters - winners
            for non_participant in non_participants:
                levels = non_participant.give_experience(awarded_exp)
                non_participant.moves.update_moves(non_participant, levels)

    def calculate_winner_entry(
        self, loser: Monster, winner: Monster
    ) -> RewardDataEntry:
        """
        Calculate rewards for a single winning monster against a defeated loser.
        """
        awarded_exp, _ = calculate_experience(loser, winner, self.damage_map)
        awarded_money = calculate_money(loser, winner)

        calculate_tps(winner, loser)
        levels = winner.give_experience(awarded_exp)

        return RewardDataEntry(
            winner=winner,
            money=awarded_money,
            experience=awarded_exp,
            levels_gained=levels,
        )

    def update_moves_and_messages(
        self, winner: Monster, entry: RewardDataEntry, rewards_data: RewardData
    ) -> None:
        """Update moves and add messages for a winner."""
        new_moves = winner.moves.update_moves(winner, entry.levels_gained)
        if new_moves:
            rewards_data.moves.extend(new_moves)

        rewards_data.messages.append(
            T.format(
                "combat_gain_exp",
                {"name": winner.name.upper(), "xp": entry.experience},
            )
        )


class TrainerRewardCalculator(RewardCalculator):
    def calculate_winner_entry(
        self, loser: Monster, winner: Monster
    ) -> RewardDataEntry:
        entry = super().calculate_winner_entry(loser, winner)
        return entry


class WildRewardCalculator(RewardCalculator):
    def calculate_winner_entry(
        self, loser: Monster, winner: Monster
    ) -> RewardDataEntry:
        entry = super().calculate_winner_entry(loser, winner)
        return entry


class HordeRewardCalculator(RewardCalculator):
    def calculate_winner_entry(
        self, loser: Monster, winner: Monster
    ) -> RewardDataEntry:
        entry = super().calculate_winner_entry(loser, winner)
        return entry


def calculate_money(loser: Monster, winner: Monster) -> int:
    """
    Calculate battle reward money.
    - Base money = loser.level * loser.money_modifier
    - Winner's held item can boost rewards (e.g. Amulet Coin).
    - Loser's held item can increase or reduce payout (e.g. Rich Charm).
    - Final payout = base_money * winner_multiplier * loser_multiplier
    """
    base_money = int(loser.level * loser.money_modifier)

    winner_multiplier = 1.0
    loser_multiplier = 1.0

    if winner.held_item and winner.held_item.money_multiplier:
        winner_multiplier = winner.held_item.money_multiplier

    if loser.held_item and loser.held_item.money_multiplier:
        loser_multiplier = loser.held_item.money_multiplier

    return int(base_money * winner_multiplier * loser_multiplier)


def calculate_tps(
    winner: Monster, loser: Monster, tp_gain: int = DEFAULT_TP_GAIN
) -> list[tuple[str, int]]:
    """
    Compares winner's stats to loser's.
    Awards training points to the winner for each stat where the opponent's value is higher.
    Returns a list of (stat_name, tp_gain) tuples.
    """
    awarded_stats = []

    logger.debug(
        f"Calculating TP for winner '{winner.name}' vs loser '{loser.name}'"
    )

    for stat_name in BasicStats.names():
        w_val = getattr(winner.base_stats, stat_name)
        l_val = getattr(loser.base_stats, stat_name)

        if l_val > w_val:
            logger.debug(
                f"Awarding {tp_gain} TP for '{stat_name}' (loser: {l_val} > winner: {w_val})"
            )
            winner.give_tps(stat_name, tp_gain)
            awarded_stats.append((stat_name, tp_gain))

    return awarded_stats


from abc import ABC, abstractmethod


class ExperienceStrategy(ABC):
    @abstractmethod
    def calculate(
        self,
        loser: Monster,
        winner: Monster,
        damages: DamageTracker,
        exp_multiplier: float,
    ) -> tuple[int, int]:
        """Calculate experience for participants and non-participants."""


class DefaultExperienceStrategy(ExperienceStrategy):
    def calculate(
        self,
        loser: Monster,
        winner: Monster,
        damages: DamageTracker,
        exp_multiplier: float,
    ) -> tuple[int, int]:
        total_exp = round(
            calculate_experience_base(
                loser.total_experience, loser.level, loser.experience_modifier
            )
            * exp_multiplier
        )

        participants = damages.get_attackers(loser)
        num_participants = len(participants) or 1
        return total_exp // num_participants, 0


class EqualExperienceStrategy(ExperienceStrategy):
    def calculate(
        self,
        loser: Monster,
        winner: Monster,
        damages: DamageTracker,
        exp_multiplier: float,
    ) -> tuple[int, int]:
        total_exp = round(
            calculate_experience_base(
                loser.total_experience, loser.level, loser.experience_modifier
            )
            * exp_multiplier
        )

        total_hits, monster_hits = damages.count_hits(loser, winner)
        proportional_exp = int(total_exp * (monster_hits / total_hits))
        return proportional_exp, 0


class FeederExperienceStrategy(ExperienceStrategy):
    def calculate(
        self,
        loser: Monster,
        winner: Monster,
        damages: DamageTracker,
        exp_multiplier: float,
    ) -> tuple[int, int]:
        total_exp = round(
            calculate_experience_base(
                loser.total_experience, loser.level, loser.experience_modifier
            )
            * exp_multiplier
        )

        participants = damages.get_attackers(loser)
        item_holder_exp = total_exp // 2
        participant_exp = (
            (total_exp - item_holder_exp) // len(participants)
            if participants
            else 0
        )

        if (
            winner.held_item
            and winner.held_item.reward_method == ExperienceMethod.XP_FEEDER
        ):
            participant_exp = item_holder_exp
        return participant_exp, 0


class TransmitterExperienceStrategy(ExperienceStrategy):
    def calculate(
        self,
        loser: Monster,
        winner: Monster,
        damages: DamageTracker,
        exp_multiplier: float,
    ) -> tuple[int, int]:
        total_exp = round(
            calculate_experience_base(
                loser.total_experience, loser.level, loser.experience_modifier
            )
            * exp_multiplier
        )

        participants = damages.get_attackers(loser)
        if not winner.owner:
            return 0, 0

        all_monsters = set(alive_party(winner.owner))
        non_participants = all_monsters - participants

        participant_exp = total_exp // 2 // (len(participants) or 1)
        non_participant_exp = total_exp // 2 // (len(non_participants) or 1)
        return participant_exp, non_participant_exp


STRATEGY_MAP = {
    ExperienceMethod.DEFAULT: DefaultExperienceStrategy(),
    ExperienceMethod.XP_EQUAL: EqualExperienceStrategy(),
    ExperienceMethod.XP_FEEDER: FeederExperienceStrategy(),
    ExperienceMethod.XP_TRANSMITTER: TransmitterExperienceStrategy(),
}


def calculate_experience(
    loser: Monster, winner: Monster, damages: DamageTracker
) -> tuple[int, int]:
    """
    Calculate experience for participants and non-participants using defined methods.

    Returns:
        tuple[int, int]: (participant_exp, non_participant_exp)
    """
    if winner.level >= MAX_LEVEL:
        return 0, 0

    exp_multiplier = winner.get_experience_multiplier()
    method = (
        winner.held_item.reward_method
        if winner.held_item
        else ExperienceMethod.DEFAULT
    )
    strategy = STRATEGY_MAP.get(method, STRATEGY_MAP[ExperienceMethod.DEFAULT])
    return strategy.calculate(loser, winner, damages, exp_multiplier)


def calculate_experience_base(
    total_experience: float, level: int, experience_modifier: float
) -> int:
    """
    Base formula for experience calculation without hits.
    """
    return int((total_experience // level) * experience_modifier)
