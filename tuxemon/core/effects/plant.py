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
class PlantEffect(CoreEffect):
    """
    Plants the item in the tilled tile the character is facing.

    Carrying this effect is what makes an item a Fruit; it must also have an
    entry in ``mods/planting.yaml`` saying how long it takes to grow. On
    success the item is consumed and a Plant of its own type appears on the
    tile, which then grows on the wall clock.

    Fails, without consuming anything, if the faced tile is not tilled or
    already has something growing in it. Because a Fruit may well have a
    second, combat-side use with its own ``use_success``/``use_failure``
    text, this effect says what happened itself; set
    ``show_dialog_on_success`` and ``show_dialog_on_failure`` to false on any
    item using it.

    **Example**

    .. code-block:: yaml

        effects:
        - type: plant
    """

    name = "plant"

    def apply_item(self, session: Session, item: Item) -> ItemEffectResult:
        target = faced_tile(session)
        if target is None:
            return ItemEffectResult(name=item.name, success=False)

        map_slug, position = target
        manager = session.client.farming_manager

        if not manager.is_plantable(item.slug):
            logger.warning(
                f"'{item.slug}' has the plant effect but no planting.yaml "
                f"entry, so it cannot be planted."
            )
            return self._fail(session, item, "planting_cannot_plant")

        tile = manager.get_tile(map_slug, position)
        if tile is None:
            return self._fail(session, item, "planting_not_tilled")
        if not tile.is_empty:
            return self._fail(session, item, "planting_occupied")

        if manager.plant(map_slug, position, item.slug) is None:
            return self._fail(session, item, "planting_cannot_plant")

        open_dialog(
            session.client,
            [T.format("planting_planted", {"name": item.name})],
        )
        return ItemEffectResult(name=item.name, success=True)

    def _fail(
        self, session: Session, item: Item, message: str
    ) -> ItemEffectResult:
        open_dialog(session.client, [T.translate(message)])
        return ItemEffectResult(name=item.name, success=False)
