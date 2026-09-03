# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.session import Session

logger = logging.getLogger(__name__)


@final
@dataclass
class SetTilledAction(EventAction):
    """
    Marks a rectangle of tiles on the current map as tilled soil.

    Tilled tiles are drawn as bare earth, can be planted with a Fruit item
    and can be watered. They are saved with the game, so a map only needs to
    run this once; tilling an already tilled tile leaves it and anything
    growing in it alone.

    Script usage:
        .. code-block::

            set_tilled <x>,<y>[,<width>][,<height>]

    Script parameters:
        x: X-coordinate of the top-left tile of the plot.
        y: Y-coordinate of the top-left tile of the plot.
        width: (Optional) Width of the plot in tiles. Defaults to 1.
        height: (Optional) Height of the plot in tiles. Defaults to 1.
    """

    name = "set_tilled"
    x: int
    y: int
    width: int = 1
    height: int = 1

    def start(self, session: Session) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError(
                f"set_tilled needs a positive size, got "
                f"{self.width}x{self.height}"
            )

        map_slug = session.client.map_manager.map_slug
        added = session.client.farming_manager.till(
            map_slug, self.x, self.y, self.width, self.height
        )
        logger.debug(
            f"Tilled {added} new tile(s) at ({self.x}, {self.y}) "
            f"{self.width}x{self.height} on '{map_slug}'."
        )
