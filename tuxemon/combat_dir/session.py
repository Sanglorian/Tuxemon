# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Any, Optional, Union

from tuxemon.states.combat.combat_classes import (
    ActionQueue,
    DamageTracker,
    EnqueuedAction,
    MenuVisibility,
)
from tuxemon.ui.combat_swap import SwapTracker

if TYPE_CHECKING:
    from tuxemon.item.item import Item
    from tuxemon.monster import Monster
    from tuxemon.npc import NPC
    from tuxemon.status.status import Status
    from tuxemon.technique.technique import Technique

logger = logging.getLogger(__name__)


class CombatSession:
    def __init__(self) -> None:
        self._turn: int = 0
        self._prize: int = 0
        self._random_tech_hit: dict[Monster, float] = {}
        self._combat_variables: dict[str, Any] = {}
        self.swap_tracker = SwapTracker()
        self.menu_visibility = MenuVisibility()
        self.damage_tracker = DamageTracker()
        self.action_queue = ActionQueue()

    # Turn management
    @property
    def turn(self) -> int:
        return self._turn

    def next_turn(self) -> int:
        self._turn += 1
        logger.debug(f"Next turn: {self._turn}")
        return self._turn

    def reset_turn(self) -> None:
        logger.debug("Turn reset to 0")
        self._turn = 0

    # Prize management
    @property
    def prize(self) -> int:
        return self._prize

    def add_prize(self, amount: int) -> None:
        self._prize += amount
        logger.debug(f"Prize increased by {amount}, total: {self._prize}")

    def reset_prize(self) -> None:
        logger.debug("Prize reset to 0")
        self._prize = 0

    # Random tech hit
    def set_tech_hit(
        self, monster: Monster, value: Optional[float] = None
    ) -> None:
        if value is None:
            value = random.random()
        self._random_tech_hit[monster] = value
        logger.debug(f"Tech hit set for {monster}: {value}")

    def get_tech_hit(self, monster: Monster) -> float:
        value = self._random_tech_hit.get(monster, 0.0)
        logger.debug(f"Tech hit retrieved for {monster}: {value}")
        return value

    def clear_tech_hits(self) -> None:
        logger.debug("Cleared all tech hits")
        self._random_tech_hit.clear()

    # Combat variables
    def set_variable(self, key: str, value: Any) -> None:
        self._combat_variables[key] = value
        logger.debug(f"Variable set: {key} = {value}")

    def get_variable(self, key: str) -> Optional[Any]:
        value = self._combat_variables.get(key)
        logger.debug(f"Variable retrieved: {key} = {value}")
        return value

    def clear_variables(self) -> None:
        logger.debug("Cleared all combat variables")
        self._combat_variables.clear()

    def enqueue_action(
        self,
        user: Union[NPC, Monster, None],
        technique: Union[Item, Technique, Status, None],
        target: Monster,
    ) -> None:
        """
        Add some technique or status to the action queue.

        Parameters:
            user: The user of the technique.
            technique: The technique used.
            target: The target of the action.
        """
        action = EnqueuedAction(user, technique, target)
        self.action_queue.enqueue(action, self.turn)

    def enqueue_damage(
        self, attacker: Monster, defender: Monster, damage: int
    ) -> None:
        """
        Add damages to damage map.

        Parameters:
            attacker: Monster.
            defender: Monster.
            damage: Quantity of damage.
        """
        self.damage_tracker.log_damage(attacker, defender, damage, self.turn)

    def reset(self) -> None:
        logger.debug("Resetting CombatSession")
        self.reset_turn()
        self.reset_prize()
        self.clear_tech_hits()
        self.clear_variables()
        self.menu_visibility.reset_to_default()
        self.damage_tracker.clear_damage()
        self.action_queue.clear_queue()
        self.action_queue.clear_history()
        self.action_queue.clear_pending()
