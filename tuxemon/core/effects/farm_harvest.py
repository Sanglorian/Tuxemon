# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, ItemEffectResult
from tuxemon.farm.targeting import resolve_target
from tuxemon.item.item import Item

if TYPE_CHECKING:
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


@dataclass
class FarmHarvestEffect(CoreEffect):
    """
    Cuts the mature crop on the tile the player is facing.

    The produce goes into the player's bag. Crops that regrow stay in the
    ground; the rest leave the soil tilled and ready to replant. Fails if
    there is nothing there, or the crop is not ready yet.

    **Example**

    .. code-block:: yaml

        effects:
        - type: farm_harvest
    """

    name = "farm_harvest"

    def apply_item(self, session: Session, item: Item) -> ItemEffectResult:
        target = resolve_target(session, "player")
        if target is None:
            return ItemEffectResult(name=item.name, success=False)

        harvested = session.client.farm_manager.harvest(
            target.map_slug, target.pos
        )
        if harvested is None:
            logger.debug(
                f"Nothing to harvest at {target.map_slug}{target.pos}"
            )
            return ItemEffectResult(name=item.name, success=False)

        produce_slug, quantity = harvested
        session.player.bag.add_item(Item.create(produce_slug), quantity)

        variables = session.player.game_variables
        variables.set("farm_harvest_item", produce_slug)
        variables.set("farm_harvest_quantity", str(quantity))

        logger.debug(f"Harvested {quantity}x {produce_slug}")
        return ItemEffectResult(
            name=item.name, success=True, extras=[produce_slug]
        )
