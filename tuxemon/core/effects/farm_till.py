# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, ItemEffectResult
from tuxemon.farm.targeting import is_tillable, resolve_target

if TYPE_CHECKING:
    from tuxemon.item.item import Item
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


@dataclass
class FarmTillEffect(CoreEffect):
    """
    Breaks the soil on the tile the player is facing, readying it for seed.

    Fails if the tile is already tilled or something is growing on it.

    **Example**

    .. code-block:: yaml

        effects:
        - type: farm_till
    """

    name = "farm_till"

    def apply_item(self, session: Session, item: Item) -> ItemEffectResult:
        target = resolve_target(session, "player")
        if target is None:
            return ItemEffectResult(name=item.name, success=False)

        if not is_tillable(session, target.pos):
            logger.debug(f"{target.pos} is not ground you can break")
            return ItemEffectResult(name=item.name, success=False)

        success = session.client.farm_manager.till(target.map_slug, target.pos)
        logger.debug(f"Tilling {target.map_slug}{target.pos}: {success}")
        return ItemEffectResult(name=item.name, success=success)
