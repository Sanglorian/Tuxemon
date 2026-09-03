# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from tuxemon.event.conditions.button_pressed import ButtonPressedCondition
from tuxemon.event.eventcondition import EventCondition
from tuxemon.farming.targeting import faced_tile
from tuxemon.session import Session


@dataclass
class ToUsePlantCondition(EventCondition):
    """
    Checks whether a character is trying to interact with a plant.

    True when the character faces a tilled tile with something growing in it
    and the INTERACT button was pressed. Pair it with ``harvest_plant`` in a
    single map event to cover a whole plot; no per-tile events are needed.

    Script usage:
        .. code-block::

            is to_use_plant <character>[,ripe]

    Script parameters:
        character: Either "player" or a character slug (e.g. "npc_maple").
        ripe: (Optional) Pass "ripe" to match only plants that have reached
            their final stage, so unripe plants can be given their own event.
    """

    name: ClassVar[str] = "to_use_plant"
    character: str
    ripe: str | None = None

    def test(self, session: Session) -> bool:
        if not ButtonPressedCondition("INTERACT").test(session):
            return False

        target = faced_tile(session, self.character)
        if target is None:
            return False

        map_slug, position = target
        manager = session.client.farming_manager
        tile = manager.get_tile(map_slug, position)
        if tile is None or tile.plant is None:
            return False

        if self.ripe == "ripe":
            return tile.plant.is_mature(manager.now())
        return True
