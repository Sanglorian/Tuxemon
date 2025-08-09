# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass

from tuxemon.event import MapCondition
from tuxemon.event.eventcondition import EventCondition
from tuxemon.session import Session

logger = logging.getLogger(__name__)


@dataclass
class BattleIsCondition(EventCondition):
    """
    Checks if a character has achieved a specific battle outcome
    against an opponent.

    Script usage:
        .. code-block::

            is battle_is <fighter>,<outcome>,<opponent>

    Script parameters:
        fighter_slug: The slug of the battle participant (e.g., "player").
        outcome: The desired battle outcome ("won", "lost", or "draw").
        opponent_slug: The slug of the opponent (e.g., "npc_maple").

    Example:
        `is battle_is player,won,npc_maple`
        Checks if the 'player' has won against 'npc_maple'.
    """

    name = "battle_is"

    def test(self, session: Session, condition: MapCondition) -> bool:
        player = session.player
        fighter, outcome, opponent = condition.parameters[:3]
        if not player.battle_handler:
            return False
        return player.battle_handler.has_fought_and_outcome(
            fighter=fighter, outcome=outcome, opponent=opponent
        )
