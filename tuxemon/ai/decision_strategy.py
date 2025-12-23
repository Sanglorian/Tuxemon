# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from tuxemon.technique.technique import Technique

if TYPE_CHECKING:
    from tuxemon.ai.ai import (
        AI,
        AIItems,
        AITechniques,
        AITrainers,
        ItemEntry,
        MonsterEntry,
        SingleTechnique,
        TechniqueCondition,
    )
    from tuxemon.ai.opponent_evaluator import OpponentEvaluator
    from tuxemon.ai.technique_tracker import TechniqueTracker
    from tuxemon.item.item import Item
    from tuxemon.monster import Monster

logger = logging.getLogger(__name__)


class AIDecisionStrategy(ABC):
    def __init__(
        self,
        evaluator: OpponentEvaluator,
        tracker: TechniqueTracker,
        ai_trainers: AITrainers,
        ai_items: AIItems,
        ai_techs: AITechniques,
    ):
        self.evaluator = evaluator
        self.tracker = tracker
        self.ai_trainers = ai_trainers
        self.ai_items = ai_items
        self.ai_techs = ai_techs

    @abstractmethod
    def make_decision(self, ai: AI) -> None:
        pass

    @abstractmethod
    def select_move(
        self, ai: AI, target: Monster
    ) -> tuple[Technique, Monster]:
        pass

    def check_ai_techs(self, user: Monster) -> Optional[SingleTechnique]:
        _config = self.ai_techs
        if user.wild:
            config = _config.techniques.get(user.slug)
        else:
            owner = user.get_owner()
            config = _config.techniques.get(owner.slug)
        return config


class TrainerAIDecisionStrategy(AIDecisionStrategy):
    def make_decision(self, ai: AI) -> None:
        """Trainer battle decision-making"""
        character_slug = ai.character.slug
        config = self.ai_trainers.trainers.get(character_slug)

        items = ai.character.items
        if items:
            for item in items:
                if self.need_healing(ai, item):
                    ai.action_item(item)
                    return

        if config is None:
            self.default_decision(ai)
            return

        monster_config = config.get(ai.monster.slug)

        if monster_config is None:
            self.default_decision(ai)
            return

        if self.handle_monster_config(ai, monster_config):
            return

        valid_actions = self.tracker.get_valid_moves(ai.opponents)
        random_action = random.choice(valid_actions)
        ai.action_tech(random_action[0], random_action[1])

    def handle_monster_config(
        self, ai: AI, monster_config: MonsterEntry
    ) -> bool:
        """Handle decision-making logic for a specific monster configuration."""
        for technique_entry in monster_config.techniques:
            technique = technique_entry.technique
            condition = technique_entry.condition

            if condition is not None and not check_tech_conditions(
                condition, ai
            ):
                continue

            valid_actions = self.tracker.get_valid_moves(ai.opponents)
            for valid_technique, opponent in valid_actions:
                if valid_technique.slug == technique:
                    ai.action_tech(valid_technique, opponent)
                    return True

        return False

    def need_healing(self, ai: AI, item: Item) -> bool:
        """
        Determines if a healing item is needed based on the AI's monster's current state.
        """
        item_entry = self.ai_items.items.get(item.slug)
        if not item_entry:
            return False

        return check_item_conditions(item_entry, ai)

    def select_move(
        self, ai: AI, target: Monster
    ) -> tuple[Technique, Monster]:
        """Select the most effective move and target."""
        valid_actions = self.tracker.get_valid_moves(ai.opponents)

        if not valid_actions:
            skip = Technique.create("skip")
            return skip, target

        config = self.check_ai_techs(ai.monster)
        if config is None:
            return random.choice(valid_actions)

        best_action = None
        highest_score = 0.0

        for technique, opponent in valid_actions:
            score = self.tracker.evaluate_technique(
                ai.monster, technique, opponent, config
            )
            logger.debug(
                f"Score: {score}, Technique: {technique.slug}, Opponent: {opponent.slug}"
            )
            if score > highest_score:
                highest_score = score
                best_action = (technique, opponent)

        return best_action or random.choice(valid_actions)

    def default_decision(self, ai: AI) -> None:
        target = self.evaluator.get_best_target()
        technique, target = self.select_move(ai, target)
        ai.action_tech(technique, target)


class WildAIDecisionStrategy(AIDecisionStrategy):
    def make_decision(self, ai: AI) -> None:
        """Wild encounter decision-making: focus on moves."""
        target = self.evaluator.get_best_target()
        technique, target = self.select_move(ai, target)
        ai.action_tech(technique, target)

    def select_move(
        self, ai: AI, target: Monster
    ) -> tuple[Technique, Monster]:
        """Select the most effective move and target."""
        valid_actions = self.tracker.get_valid_moves(ai.opponents)

        if not valid_actions:
            skip = Technique.create("skip")
            return skip, target

        config = self.check_ai_techs(ai.monster)
        if config is None:
            return random.choice(valid_actions)

        best_action = None
        highest_score = 0.0

        for technique, opponent in valid_actions:
            score = self.tracker.evaluate_technique(
                ai.monster, technique, opponent, config
            )
            if score > highest_score:
                highest_score = score
                best_action = (technique, opponent)

        return best_action or random.choice(valid_actions)


def check_item_conditions(item_entry: ItemEntry, ai: AI) -> bool:
    """
    Check if all conditions for a technique are met.
    """
    hp_ratio = ai.monster.hp_ratio

    if item_entry.hp_below and hp_ratio >= item_entry.hp_below:
        return False

    if item_entry.hp_above and hp_ratio <= item_entry.hp_above:
        return False

    if item_entry.hp_range and not (
        item_entry.hp_range[0] <= hp_ratio < item_entry.hp_range[1]
    ):
        return False

    if item_entry.status_effects and not any(
        ai.monster.status.has_status(status)
        for status in item_entry.status_effects
    ):
        return False

    if (
        item_entry.monster_slugs
        and ai.monster.slug not in item_entry.monster_slugs
    ):
        return False

    return True


def check_tech_conditions(condition: TechniqueCondition, ai: AI) -> bool:
    """
    Check if all conditions for a technique are met.
    """
    current_turn = ai.session.client.combat_session.turn
    monster_health = ai.monster.hp_ratio

    if condition.always:
        return True

    if condition.turn is not None and current_turn != condition.turn:
        return False

    if condition.hp_below is not None and monster_health >= condition.hp_below:
        return False

    if condition.hp_above is not None and monster_health <= condition.hp_above:
        return False

    if condition.hp_range and not (
        condition.hp_range[0] <= monster_health <= condition.hp_range[1]
    ):
        return False

    if condition.status_effects:
        return any(
            ai.monster.status.has_status(status)
            for status in condition.status_effects
        )

    if condition.opponent_status:
        if not ai.session.client.combat_session.is_double:
            return any(
                ai.opponents[0].status.has_status(opponent_status)
                for opponent_status in condition.opponent_status
            )

    if condition.opponent_types:
        if not ai.session.client.combat_session.is_double:
            return any(
                ai.opponents[0].has_type(opponent_type)
                for opponent_type in condition.opponent_types
            )

    if condition.opponent_slugs:
        if not ai.session.client.combat_session.is_double:
            return ai.opponents[0].slug in condition.opponent_slugs

    return True
