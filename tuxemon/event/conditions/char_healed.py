# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass

from tuxemon.db import SpatialCondition
from tuxemon.event.eventcondition import EventCondition
from tuxemon.session import Session

logger = logging.getLogger(__name__)


@dataclass
class CharHealedCondition(EventCondition):
    """
    Check whether all monsters in the character's party are healed.

    Script usage:
        .. code-block::

            is char_healed <character>

    Script parameters:
        character: Either "player" or NPC slug name (e.g. "npc_maple")
    """

    name = "char_healed"

    def test(self, session: Session, condition: SpatialCondition) -> bool:
        character = session.get_npc(condition.parameters[0])
        if character is None:
            logger.error(f"{condition.parameters[0]} not found")
            return False

        if not character.monsters:
            return False

        return character.party.is_healed
