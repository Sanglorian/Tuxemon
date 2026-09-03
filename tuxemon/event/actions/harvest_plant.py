# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.farming.targeting import faced_tile
from tuxemon.item.item import Item
from tuxemon.locale.locale import T
from tuxemon.session import Session
from tuxemon.tools import open_dialog

logger = logging.getLogger(__name__)


@final
@dataclass
class HarvestPlantAction(EventAction):
    """
    Harvests the plant the character is facing, if it is fully grown.

    A fully grown plant hands over ``ceil(2 * yield)`` of its own Fruit, where
    the yield runs from 1.0 for a plant that was never watered to 2.0 for one
    watered for the whole of its growth. The tile stays tilled and can be
    replanted straight away.

    A plant that is not fully grown gives nothing and stays where it is; the
    character is told how it is getting on.

    Script usage:
        .. code-block::

            harvest_plant [character]

    Script parameters:
        character: (Optional) Either "player" or a character slug. Defaults
            to "player".
    """

    name = "harvest_plant"
    character: str | None = None

    def start(self, session: Session) -> None:
        character_slug = self.character or "player"
        target = faced_tile(session, character_slug)
        if target is None:
            return

        map_slug, position = target
        manager = session.client.farming_manager
        tile = manager.get_tile(map_slug, position)
        if tile is None or tile.plant is None:
            return

        character = session.client.get_npc(character_slug)
        if character is None:
            logger.error(f"Character '{character_slug}' not found.")
            return

        fruit_name = T.translate(tile.plant.fruit)
        harvested = manager.harvest(map_slug, position)
        if harvested is None:
            open_dialog(
                session.client,
                [T.format("planting_still_growing", {"name": fruit_name})],
            )
            return

        fruit, quantity = harvested
        existing = character.bag.find_item(fruit)
        if existing:
            existing.increase_quantity(quantity)
        else:
            character.bag.add_item(Item.create(fruit), quantity)

        open_dialog(
            session.client,
            [
                T.format(
                    "planting_harvested",
                    {"name": fruit_name, "quantity": quantity},
                )
            ],
        )
