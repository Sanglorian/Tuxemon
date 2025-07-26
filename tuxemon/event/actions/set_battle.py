# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import final

from tuxemon.battle import Battle
from tuxemon.db import OutputBattle
from tuxemon.event.eventaction import EventAction
from tuxemon.session import Session

logger = logging.getLogger(__name__)


@final
@dataclass
class SetBattleAction(EventAction):
    """
    Appends a new battle to the player's battle history.

    Script usage:
        .. code-block::

            set_battle <fighter>,<result>,<opponent>

    Script parameters:
        fighter_slug: The slug of the battle participant (e.g., "player").
        outcome: The desired battle outcome ("won", "lost", or "draw").
        opponent_slug: The slug of the opponent (e.g., "npc_maple").

    Example:
        `set_battle player,won,npc_maple`
        Add the 'player' has won against 'npc_maple' to the history.
    """

    name = "set_battle"
    fighter_slug: str
    outcome: str
    opponent_slug: str

    def start(self, session: Session) -> None:
        player = session.player

        if self.outcome not in list(OutputBattle):
            raise ValueError(
                f"{self.outcome} isn't among {list(OutputBattle)}"
            )

        data = {
            "fighter": self.fighter_slug,
            "opponent": self.opponent_slug,
            "outcome": OutputBattle(self.outcome),
            "steps": int(player.steps),
        }
        battle = Battle(data)
        logger.info(
            f"{self.fighter_slug} {self.outcome} against {self.opponent_slug}"
        )
        player.battle_handler.add_battle(battle)
