# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import final

from tuxemon.db import StatType
from tuxemon.event.eventaction import EventAction
from tuxemon.monster.monster import Monster
from tuxemon.session import Session
from tuxemon.tools import get_valid_uuid

logger = logging.getLogger(__name__)


@final
@dataclass
class ResetTpAction(EventAction):
    """
    Reset the training points (TP) of a monster in the current player's party.

    Unlike ``modify_monster_stats`` (which adjusts custom stat boosts), this
    action zeroes a monster's earned training points, then recomputes its
    final stats. This lets an NPC wipe a monster's training, either for a
    single statistic or for every statistic at once.

    Script usage:
        .. code-block::

            reset_tp [variable][,stat]

    Script parameters:
        variable: Name of the variable where to store the monster id. If no
            variable is specified, all monsters are touched.
        stat: A stat among armour, dodge, hp, melee, speed and ranged. If no
            stat, then all the stats are reset.

    eg. "reset_tp" (reset every stat on the whole party)
    eg. "reset_tp name_variable" (reset every stat on one monster)
    eg. "reset_tp name_variable,armour" (reset only armour on one monster)
    """

    name = "reset_tp"
    variable: str | None = None
    stat: str | None = None

    def start(self, session: Session) -> None:
        player = session.player
        if not player.monsters:
            self.stop()
            return
        if self.stat and self.stat not in list(StatType):
            raise ValueError(f"{self.stat} isn't among {list(StatType)}")

        stats = [StatType(self.stat)] if self.stat else list(StatType)

        def reset_monster_tp(monster: Monster) -> None:
            for stat in stats:
                monster.training_points.set_stat(stat.value, 0)
            monster.training_points.validate()
            monster.set_stats()

        if self.variable is None:
            for mon in player.monsters:
                reset_monster_tp(mon)
        else:
            monster_id = get_valid_uuid(player.game_variables, self.variable)
            if monster_id is None:
                logger.info(
                    f"No valid monster selected for variable '{self.variable}'"
                )
                self.stop()
                return  # Exit early if no valid UUID
            monster = session.client.get_monster_by_iid(monster_id)
            if monster is None:
                logger.error("Monster not found")
                self.stop()
                return

            reset_monster_tp(monster)
