# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from typing import Any

from tuxemon.farm.calendar import FarmCalendar
from tuxemon.farm.crop import lookup_crop
from tuxemon.farm.grid import FarmGrid, FarmTile, TilePos

logger = logging.getLogger(__name__)


class FarmManager:
    """
    Owns the farm's persistent tile grid and its day counter, and applies the
    season rules that connect the two.

    This is the single object the rest of the engine talks to: the client
    holds one, the renderer reads from it, and the world state saves it.
    """

    def __init__(self) -> None:
        self.grid = FarmGrid()
        self.calendar = FarmCalendar()

    # -- queries --------------------------------------------------------

    def get_tile(self, map_slug: str, pos: TilePos) -> FarmTile | None:
        """Returns the tile state, or ``None`` if the tile is untouched."""
        return self.grid.get_tile(map_slug, pos)

    # -- player actions -------------------------------------------------

    def till(self, map_slug: str, pos: TilePos) -> bool:
        """Breaks the soil on a tile."""
        return self.grid.till(map_slug, pos)

    def water(self, map_slug: str, pos: TilePos) -> bool:
        """Waters a tilled tile."""
        return self.grid.water(map_slug, pos)

    def plant(self, map_slug: str, pos: TilePos, crop_slug: str) -> bool:
        """
        Plants a crop on a tilled tile, if the crop grows in this season.
        """
        crop = lookup_crop(crop_slug)
        if crop is None:
            logger.error(f"Unknown crop '{crop_slug}'")
            return False

        if not crop.grows_in(self.calendar.season):
            logger.debug(
                f"Crop '{crop_slug}' does not grow in {self.calendar.season}"
            )
            return False

        return self.grid.plant(map_slug, pos, crop_slug, self.calendar.day)

    def harvest(self, map_slug: str, pos: TilePos) -> tuple[str, int] | None:
        """Harvests a mature crop, returning ``(produce_item, quantity)``."""
        return self.grid.harvest(map_slug, pos)

    def clear(self, map_slug: str, pos: TilePos) -> bool:
        """Clears a tile back to untouched ground."""
        return self.grid.clear(map_slug, pos)

    # -- daily tick -----------------------------------------------------

    def advance_day(self, days: int = 1) -> int:
        """
        Ends the farm day: grows every crop, dries the soil, and moves the
        farm calendar forward. Returns the new farm day.

        This is what a bed calls. It never touches the session's real-world
        clock.
        """
        for _ in range(days):
            self.grid.advance_day()
        return self.calendar.advance_day(days)

    # -- persistence ----------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Prepares a dictionary of the farm to be saved."""
        return {
            "calendar": self.calendar.get_state(),
            "grid": self.grid.get_state(),
        }

    def set_state(self, save_data: dict[str, Any]) -> None:
        """Recreates the farm from saved data."""
        if not save_data:
            return
        self.calendar.set_state(save_data.get("calendar", {}))
        self.grid.set_state(save_data.get("grid", {}))
