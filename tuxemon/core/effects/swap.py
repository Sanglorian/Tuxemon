# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, TechEffectResult

if TYPE_CHECKING:
    from tuxemon.monster import Monster
    from tuxemon.session import Session
    from tuxemon.technique.technique import Technique

logger = logging.getLogger(__name__)


@dataclass
class SwapEffect(CoreEffect):
    """
    Used just for combat: change order of monsters.

    Position of monster in party will be changed.
    """

    name = "swap"

    def apply_tech_target(
        self, session: Session, tech: Technique, user: Monster, target: Monster
    ) -> TechEffectResult:
        player = user.get_owner()
        combat_state = tech.get_combat_state()

        logger.debug(
            f"Initiating swap: removing {user.name}, adding {target.name}"
        )

        def swap_add(removed: Monster) -> None:
            logger.debug(
                f"Swap add triggered: replacing {removed.name} with {target.name}"
            )
            combat_state.add_monster_into_play(player, target, removed)

        combat_state._action_queue.swap(user, target)
        logger.debug(f"Action queue updated: {user.name} > {target.name}")

        combat_state.remove_monster_from_play(user)
        logger.debug(f"{user.name} removed from play")

        combat_state.task(partial(swap_add, user), interval=0.75)

        return TechEffectResult(name=tech.name, success=True)
