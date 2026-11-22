# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar

from tuxemon.event.eventcondition import EventCondition
from tuxemon.session import Session

logger = logging.getLogger(__name__)


@dataclass
class CharAtTeleportFaintCondition(EventCondition):
    """
    Check whether the character is on the map stored in their teleport_faint.

    Only the map is compared, not the exact tile, so the condition stays
    ``True`` while the character walks around their recovery point.

    Script usage:
        .. code-block::

            is char_at_teleport_faint <character>

    Script parameters:
        character: Either "player" or npc slug name (e.g. "npc_maple")
    """

    name: ClassVar[str] = "char_at_teleport_faint"
    character: str

    def test(self, session: Session) -> bool:
        character = session.client.get_npc(self.character)
        if character is None:
            logger.error(f"{self.character} not found")
            return False

        return character.current_map == character.teleport_faint.map_name
