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
class FarmPlantEffect(CoreEffect):
    """
    Sows a seed on the tilled tile the player is facing.

    Fails if the tile is not tilled, already has a crop, or the crop does not
    grow in the current farm season.

    The seed is spent here rather than by the item pipeline, so that seed bags
    carry ``consumable: false``. The pipeline consumes a failed item whenever
    ``items_consumed_on_failure`` is set, which is the default, and losing a
    seed to a mistimed swing at a wall is not a cost worth charging.

    **Parameters**
    - ``crop``: The crop slug to plant, as defined in ``crops.yaml``.

    **Example**

    .. code-block:: yaml

        effects:
        - type: farm_plant
          parameters:
          - turnip
    """

    name = "farm_plant"
    crop: str

    def apply_item(self, session: Session, item: Item) -> ItemEffectResult:
        target = resolve_target(session, "player")
        if target is None:
            return ItemEffectResult(name=item.name, success=False)

        success = session.client.farm_manager.plant(
            target.map_slug, target.pos, self.crop
        )
        if success:
            session.player.bag.remove_item(item, 1)

        logger.debug(
            f"Planting {self.crop} at {target.map_slug}{target.pos}: {success}"
        )
        return ItemEffectResult(name=item.name, success=success)
