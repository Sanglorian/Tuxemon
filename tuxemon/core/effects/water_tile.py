# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, ItemEffectResult
from tuxemon.farming.targeting import faced_tile
from tuxemon.locale.locale import T
from tuxemon.tools import open_dialog

if TYPE_CHECKING:
    from tuxemon.item.item import Item
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


@dataclass
class WaterTileEffect(CoreEffect):
    """
    Waters the tilled tile the character is facing.

    The watering timestamp is recorded on the tile rather than on the plant,
    so watering a tilled tile before anything goes into it still counts once
    something is planted. Watering ground that has not been tilled fails and
    says so.

    A watering keeps the tile wet for 24 hours from the moment it is made;
    watering again while the tile is still wet restarts that 24 hours rather
    than stacking on top of it.

    **Example**

    .. code-block:: yaml

        effects:
        - type: water_tile
    """

    name = "water_tile"

    def apply_item(self, session: Session, item: Item) -> ItemEffectResult:
        target = faced_tile(session)
        if target is None:
            return ItemEffectResult(name=item.name, success=False)

        map_slug, position = target
        manager = session.client.farming_manager

        if not manager.water(map_slug, position):
            open_dialog(session.client, [T.translate("watering_nothing_here")])
            return ItemEffectResult(name=item.name, success=False)

        tile = manager.get_tile(map_slug, position)
        message = (
            "watering_watered"
            if tile is not None and tile.plant is not None
            else "watering_watered_soil"
        )
        open_dialog(session.client, [T.translate(message)])
        return ItemEffectResult(name=item.name, success=True)
