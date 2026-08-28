# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, ItemEffectResult
from tuxemon.farm.targeting import resolve_target

if TYPE_CHECKING:
    from tuxemon.item.item import Item
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


@dataclass
class FarmWaterEffect(CoreEffect):
    """
    Waters the tilled tile the player is facing.

    Crops only grow on days they were watered, and wither once they have been
    dry for longer than the crop tolerates. Fails if the tile is not tilled,
    or has already been watered today.

    **Example**

    .. code-block:: yaml

        effects:
        - type: farm_water
    """

    name = "farm_water"

    def apply_item(self, session: Session, item: Item) -> ItemEffectResult:
        target = resolve_target(session, "player")
        if target is None:
            return ItemEffectResult(name=item.name, success=False)

        success = session.client.farm_manager.water(
            target.map_slug, target.pos
        )
        logger.debug(f"Watering {target.map_slug}{target.pos}: {success}")
        return ItemEffectResult(name=item.name, success=success)
