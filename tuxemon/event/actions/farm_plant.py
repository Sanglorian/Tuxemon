# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.farm.crop import lookup_crop
from tuxemon.farm.targeting import resolve_target, set_result
from tuxemon.session import Session

logger = logging.getLogger(__name__)


@final
@dataclass
class FarmPlantAction(EventAction):
    """
    Plant a crop on the tilled tile the character is facing.

    Fails if the tile is not tilled, already has a crop, the crop does not
    grow in the current farm season, or the character is out of seeds.
    Sets the ``farm_result`` game variable to "true" or "false".

    Script usage:
        .. code-block::

            farm_plant <character>,<crop>[,consume_seed]

    Script parameters:
        character: Either "player" or character slug name (e.g. "npc_maple").
        crop: Crop slug, as defined in ``crops.yaml`` (e.g. "turnip").
        consume_seed: Whether to require and spend the crop's seed item.
            Defaults to true.
    """

    name = "farm_plant"
    character: str
    crop: str
    consume_seed: bool = True

    def start(self, session: Session) -> None:
        target = resolve_target(session, self.character)
        if target is None:
            set_result(session, False)
            return

        npc = session.client.get_npc(self.character)
        model = lookup_crop(self.crop)
        if npc is None or model is None:
            logger.error(f"Cannot plant unknown crop '{self.crop}'")
            set_result(session, False)
            return

        seed = (
            npc.bag.find_item(model.seed_item) if self.consume_seed else None
        )
        if self.consume_seed and seed is None:
            logger.debug(f"{self.character} has no {model.seed_item}")
            set_result(session, False)
            return

        success = session.client.farm_manager.plant(
            target.map_slug, target.pos, self.crop
        )
        if success and seed is not None:
            npc.bag.remove_item(seed, 1)

        logger.debug(
            f"Planting {self.crop} at {target.map_slug}{target.pos}: {success}"
        )
        set_result(session, success)
