# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass

from tuxemon.db import SpatialCondition
from tuxemon.event.eventcondition import EventCondition
from tuxemon.session import Session


@dataclass
class CharExistsCondition(EventCondition):
    """
    Check to see if a character object exists in the current list of NPCs.

    Script usage:
        .. code-block::

            is char_exists <character>

    Script parameters:
        character: Either "player" or character slug name (e.g. "npc_maple").

    """

    name = "char_exists"

    def test(self, session: Session, condition: SpatialCondition) -> bool:
        return session.get_npc(condition.parameters[0]) is not None
