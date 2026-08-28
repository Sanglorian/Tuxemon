# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.farm.targeting import resolve_target, set_result
from tuxemon.session import Session

logger = logging.getLogger(__name__)


@final
@dataclass
class FarmTillAction(EventAction):
    """
    Break the soil on the tile the character is facing.

    Fails if the tile is already tilled or something is growing on it.
    Sets the ``farm_result`` game variable to "true" or "false".

    Script usage:
        .. code-block::

            farm_till <character>

    Script parameters:
        character: Either "player" or character slug name (e.g. "npc_maple").
    """

    name = "farm_till"
    character: str

    def start(self, session: Session) -> None:
        target = resolve_target(session, self.character)
        if target is None:
            set_result(session, False)
            return

        success = session.client.farm_manager.till(target.map_slug, target.pos)
        logger.debug(f"Tilling {target.map_slug}{target.pos}: {success}")
        set_result(session, success)
