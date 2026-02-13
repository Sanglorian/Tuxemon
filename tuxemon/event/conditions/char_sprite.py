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
class CharSpriteCondition(EventCondition):
    """
    Check the character's sprite

    Script usage:
        .. code-block::

            is char_sprite <character>,<sprite>

    Script parameters:
        character: Either "player" or character slug name (e.g. "npc_maple")
        sprite: NPC's sprite (eg maniac, florist, etc.)
    """

    name = "char_sprite"

    def test(self, session: Session, condition: SpatialCondition) -> bool:
        target_slug = condition.parameters[0]
        expected_sprite = condition.parameters[1]

        target = session.get_npc(target_slug)
        if not target:
            return False

        return target.appearance_manager.state.sprite_name == expected_sprite
