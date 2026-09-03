# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Owns every tilled tile in the game and answers questions about them.

The manager keeps no timers and does no per-frame work: it stores absolute
timestamps and derives everything else when asked. The wall clock is injected
so tests and the headless demo can fast-forward without waiting.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator, Mapping
from typing import Any

from tuxemon.farming.config import PlantingConfig, get_planting_config
from tuxemon.farming.plot import Plant, TilledTile

logger = logging.getLogger(__name__)

TilePos = tuple[int, int]

#: Render layer for the soil, below the layer NPC sprites are drawn on.
SOIL_LAYER = 1

#: Render layer for the plant itself, alongside NPC sprites.
PLANT_LAYER = 2


class FarmingManager:
    """
    Tilled tiles and the plants in them, keyed by map slug.

    Parameters:
        clock: Returns the current wall-clock time in seconds since the
            epoch. Only replaced by tests and the headless demo.
        config: Planting config to use. Defaults to ``mods/planting.yaml``.
    """

    def __init__(
        self,
        clock: Callable[[], float] = time.time,
        config: PlantingConfig | None = None,
    ) -> None:
        self.clock = clock
        self._config = config
        self.plots: dict[str, dict[TilePos, TilledTile]] = {}

    @property
    def config(self) -> PlantingConfig:
        if self._config is None:
            self._config = get_planting_config()
        return self._config

    def now(self) -> float:
        return self.clock()

    # -- tilling ---------------------------------------------------------

    def till(
        self,
        map_slug: str,
        x: int,
        y: int,
        width: int = 1,
        height: int = 1,
    ) -> int:
        """
        Mark a rectangle of tiles as tilled, leaving already-tilled ones alone.

        Parameters:
            map_slug: Map the tiles belong to.
            x: Left edge of the rectangle, in tiles.
            y: Top edge of the rectangle, in tiles.
            width: Width in tiles, at least 1.
            height: Height in tiles, at least 1.

        Returns:
            How many tiles were newly tilled.
        """
        plot = self.plots.setdefault(map_slug, {})
        added = 0
        for offset_y in range(max(height, 1)):
            for offset_x in range(max(width, 1)):
                position = (x + offset_x, y + offset_y)
                if position not in plot:
                    plot[position] = TilledTile()
                    added += 1
        return added

    def untill(self, map_slug: str, x: int, y: int) -> bool:
        """Remove a tilled tile and anything growing in it."""
        plot = self.plots.get(map_slug)
        if plot is None or (x, y) not in plot:
            return False
        del plot[(x, y)]
        return True

    def is_tilled(self, map_slug: str, position: TilePos) -> bool:
        return position in self.plots.get(map_slug, {})

    def get_tile(self, map_slug: str, position: TilePos) -> TilledTile | None:
        return self.plots.get(map_slug, {}).get(position)

    def tiles(self, map_slug: str) -> Iterator[tuple[TilePos, TilledTile]]:
        """Every tilled tile on a map, in no particular order."""
        return iter(self.plots.get(map_slug, {}).items())

    # -- planting, watering, harvesting -----------------------------------

    def is_plantable(self, fruit: str) -> bool:
        """Whether an item slug can be planted at all."""
        return self.config.is_plantable(fruit)

    def plant(
        self, map_slug: str, position: TilePos, fruit: str
    ) -> Plant | None:
        """
        Put a fruit in the ground.

        Parameters:
            map_slug: Map the tile belongs to.
            position: Tile to plant in.
            fruit: Item slug being planted.

        Returns:
            The new plant, or None if the tile is not tilled, already has a
            plant, or the item is not plantable.
        """
        fruit_config = self.config.get(fruit)
        if fruit_config is None:
            logger.debug(f"'{fruit}' is not a plantable item.")
            return None

        tile = self.get_tile(map_slug, position)
        if tile is None:
            logger.debug(f"{position} on '{map_slug}' is not tilled.")
            return None
        if tile.plant is not None:
            logger.debug(f"{position} on '{map_slug}' already has a plant.")
            return None

        # Copy the durations onto the plant so retuning the config later
        # cannot rewrite the growth of something already in the ground.
        tile.plant = Plant(
            fruit=fruit,
            planted_at=self.now(),
            stage_seconds=list(fruit_config.stage_seconds),
        )
        logger.info(f"Planted '{fruit}' at {position} on '{map_slug}'.")
        return tile.plant

    def water(self, map_slug: str, position: TilePos) -> bool:
        """
        Water a tilled tile.

        Watering an empty tilled tile is allowed: the timestamp lives on the
        tile, so it still counts towards whatever is planted next.

        Returns:
            True if the tile was tilled and the watering was recorded.
        """
        tile = self.get_tile(map_slug, position)
        if tile is None:
            return False
        tile.water(self.now())
        return True

    def can_harvest(self, map_slug: str, position: TilePos) -> bool:
        """Whether the tile holds a plant that has reached its final stage."""
        tile = self.get_tile(map_slug, position)
        return (
            tile is not None
            and tile.plant is not None
            and tile.plant.is_mature(self.now())
        )

    def harvest(
        self, map_slug: str, position: TilePos
    ) -> tuple[str, int] | None:
        """
        Take a fully grown plant out of the ground.

        The tile stays tilled and keeps any watering that is still keeping it
        wet, so it can be replanted straight away.

        Returns:
            ``(fruit slug, quantity)``, or None if there is nothing ripe here.
        """
        tile = self.get_tile(map_slug, position)
        if tile is None or tile.plant is None:
            return None

        now = self.now()
        plant = tile.plant
        if not plant.is_mature(now):
            return None

        amount = tile.harvest_amount(now)
        tile.plant = None
        tile.prune_waterings(now)
        logger.info(
            f"Harvested {amount} x '{plant.fruit}' at {position} "
            f"on '{map_slug}'."
        )
        return plant.fruit, amount

    # -- rendering --------------------------------------------------------

    def render_entries(self, map_slug: str) -> list[tuple[str, TilePos, int]]:
        """
        Sprites to draw for a map's plot this frame.

        Returns:
            ``(sprite path, tile position, render layer)`` for the soil of
            every tilled tile, plus the current stage sprite of every plant.
        """
        now = self.now()
        config = self.config
        entries: list[tuple[str, TilePos, int]] = []

        for position, tile in sorted(self.plots.get(map_slug, {}).items()):
            soil = (
                config.tilled_wet_sprite
                if tile.is_wet(now)
                else config.tilled_sprite
            )
            entries.append((soil, position, SOIL_LAYER))

            plant = tile.plant
            if plant is None:
                continue
            fruit_config = config.get(plant.fruit)
            if fruit_config is None or not fruit_config.stages:
                continue
            index = min(plant.stage(now), len(fruit_config.stages) - 1)
            entries.append((fruit_config.stages[index], position, PLANT_LAYER))

        return entries

    # -- persistence ------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """
        Serialise every plot to plain JSON-encodable data.

        Tile positions become ``"x,y"`` strings so the result survives every
        save backend, JSON included.
        """
        return {
            map_slug: {
                f"{x},{y}": tile.to_dict()
                for (x, y), tile in sorted(plot.items())
            }
            for map_slug, plot in sorted(self.plots.items())
            if plot
        }

    def set_state(self, state: Mapping[str, Any] | None) -> None:
        """Replace every plot with saved data, dropping unreadable tiles."""
        self.plots = {}
        for map_slug, plot in (state or {}).items():
            tiles: dict[TilePos, TilledTile] = {}
            for key, raw_tile in (plot or {}).items():
                try:
                    x, y = (int(part) for part in str(key).split(","))
                    tiles[(x, y)] = TilledTile.from_dict(raw_tile)
                except (KeyError, TypeError, ValueError) as e:
                    logger.error(
                        f"Dropping unreadable tilled tile '{key}' on "
                        f"'{map_slug}': {e}"
                    )
            if tiles:
                self.plots[str(map_slug)] = tiles
