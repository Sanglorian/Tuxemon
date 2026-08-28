# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.farm.targeting import resolve_target, set_result
from tuxemon.item.item import Item
from tuxemon.session import Session

logger = logging.getLogger(__name__)


@final
@dataclass
class FarmHarvestAction(EventAction):
    """
    Harvest the mature crop on the tile the character is facing.

    The produce goes into the character's bag. Crops that regrow stay in the
    ground; the rest leave the soil tilled and ready to replant. Fails if
    there is nothing there, or the crop is not ready yet.
    Sets the ``farm_result`` game variable to "true" or "false", and the
    ``farm_harvest_item`` and ``farm_harvest_quantity`` variables to describe
    what was picked.

    Script usage:
        .. code-block::

            farm_harvest <character>

    Script parameters:
        character: Either "player" or character slug name (e.g. "npc_maple").
    """

    name = "farm_harvest"
    character: str

    def start(self, session: Session) -> None:
        target = resolve_target(session, self.character)
        npc = session.client.get_npc(self.character)
        if target is None or npc is None:
            set_result(session, False)
            return

        harvested = session.client.farm_manager.harvest(
            target.map_slug, target.pos
        )
        if harvested is None:
            logger.debug(
                f"Nothing to harvest at {target.map_slug}{target.pos}"
            )
            set_result(session, False)
            return

        item_slug, quantity = harvested
        npc.bag.add_item(Item.create(item_slug), quantity)

        variables = session.player.game_variables
        variables.set("farm_harvest_item", item_slug)
        variables.set("farm_harvest_quantity", str(quantity))
        logger.debug(f"Harvested {quantity}x {item_slug}")
        set_result(session, True)
