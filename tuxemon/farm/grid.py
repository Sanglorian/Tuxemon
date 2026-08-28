# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from tuxemon.farm.crop import PlantedCrop, lookup_crop

logger = logging.getLogger(__name__)

TilePos = tuple[int, int]


@dataclass
class FarmTile:
    """
    The state of one farmable tile.

    Soil holds the water, not the plant, so ``watered`` survives a crop being
    harvested and replanted on the same tile.
    """

    tilled: bool = False
    watered: bool = False
    crop: PlantedCrop | None = None

    @property
    def is_empty(self) -> bool:
        """Whether the tile carries no state worth remembering."""
        return not self.tilled and not self.watered and self.crop is None

    def get_state(self) -> dict[str, Any]:
        """Prepares a dictionary of the tile to be saved."""
        state: dict[str, Any] = {
            "tilled": self.tilled,
            "watered": self.watered,
        }
        if self.crop is not None:
            state["crop"] = self.crop.get_state()
        return state

    @classmethod
    def from_state(cls, save_data: dict[str, Any]) -> FarmTile:
        """Recreates a tile from saved data."""
        raw_crop = save_data.get("crop")
        return cls(
            tilled=bool(save_data.get("tilled", False)),
            watered=bool(save_data.get("watered", False)),
            crop=PlantedCrop.from_state(raw_crop) if raw_crop else None,
        )


class FarmGrid:
    """
    Persistent per-tile farm state, keyed by map slug and tile coordinate.

    The engine's ``surface_map`` is rebuilt from the Tiled file on every map
    load and is never saved, so it cannot remember that a tile was tilled
    yesterday. This grid is that memory. It is deliberately independent of
    which map is currently loaded: :meth:`advance_day` grows crops on every
    map the player has ever farmed, not just the one they are standing on.
    """

    def __init__(self) -> None:
        self._maps: dict[str, dict[TilePos, FarmTile]] = {}

    # -- lookup ---------------------------------------------------------

    def get_tile(self, map_slug: str, pos: TilePos) -> FarmTile | None:
        """Returns the tile state, or ``None`` if the tile is untouched."""
        return self._maps.get(map_slug, {}).get(pos)

    def tiles(self, map_slug: str) -> Iterator[tuple[TilePos, FarmTile]]:
        """Iterates over every remembered tile on one map."""
        yield from self._maps.get(map_slug, {}).items()

    def map_slugs(self) -> list[str]:
        """Every map with remembered farm state."""
        return list(self._maps)

    def tile_count(self) -> int:
        """Total number of remembered tiles across all maps."""
        return sum(len(tiles) for tiles in self._maps.values())

    def _ensure_tile(self, map_slug: str, pos: TilePos) -> FarmTile:
        tiles = self._maps.setdefault(map_slug, {})
        tile = tiles.get(pos)
        if tile is None:
            tile = FarmTile()
            tiles[pos] = tile
        return tile

    # -- mutation -------------------------------------------------------

    def till(self, map_slug: str, pos: TilePos) -> bool:
        """
        Breaks the soil on a tile. Returns ``False`` if it was already tilled
        or something is growing there.
        """
        tile = self.get_tile(map_slug, pos)
        if tile is not None and (tile.tilled or tile.crop is not None):
            return False

        self._ensure_tile(map_slug, pos).tilled = True
        return True

    def water(self, map_slug: str, pos: TilePos) -> bool:
        """
        Waters a tile. Returns ``False`` unless the tile is tilled and dry.
        """
        tile = self.get_tile(map_slug, pos)
        if tile is None or not tile.tilled or tile.watered:
            return False

        tile.watered = True
        return True

    def plant(
        self, map_slug: str, pos: TilePos, crop_slug: str, day: int
    ) -> bool:
        """
        Plants a seed on a tilled, empty tile.

        Parameters:
            map_slug: Map the tile belongs to.
            pos: Tile coordinate.
            crop_slug: Crop to plant, as defined in ``crops.yaml``.
            day: The farm day the crop was planted on.
        """
        tile = self.get_tile(map_slug, pos)
        if tile is None or not tile.tilled or tile.crop is not None:
            return False

        if lookup_crop(crop_slug) is None:
            logger.error(f"Unknown crop '{crop_slug}'")
            return False

        tile.crop = PlantedCrop(slug=crop_slug, planted_day=day)
        return True

    def harvest(self, map_slug: str, pos: TilePos) -> tuple[str, int] | None:
        """
        Harvests a mature crop.

        Returns the ``(produce_item, quantity)`` produced, or ``None`` if
        there was nothing ready. One-off crops are cleared from the tile,
        leaving the soil tilled and ready to replant; regrowing crops stay.
        """
        tile = self.get_tile(map_slug, pos)
        if tile is None or tile.crop is None:
            return None

        model = tile.crop.model
        if model is None:
            logger.error(f"Crop '{tile.crop.slug}' has no definition")
            return None

        quantity = tile.crop.harvest(model)
        if quantity == 0:
            return None

        if tile.crop.is_spent(model):
            tile.crop = None

        return model.produce_item, quantity

    def clear(self, map_slug: str, pos: TilePos) -> bool:
        """
        Removes whatever is growing on a tile and forgets the tile if nothing
        is left to remember. Returns ``False`` if the tile was already empty.
        """
        tiles = self._maps.get(map_slug)
        if tiles is None or pos not in tiles:
            return False

        del tiles[pos]
        if not tiles:
            del self._maps[map_slug]
        return True

    # -- daily tick -----------------------------------------------------

    def advance_day(self) -> None:
        """
        Applies one farm day to every remembered tile on every map.

        Crops grow on the water they were given during the day that just
        ended, then the soil dries out overnight.
        """
        for map_slug, tiles in self._maps.items():
            for pos, tile in tiles.items():
                if tile.crop is not None:
                    model = tile.crop.model
                    if model is None:
                        logger.error(
                            f"Crop '{tile.crop.slug}' at {map_slug}{pos} "
                            "has no definition; skipping growth"
                        )
                    else:
                        tile.crop.advance_day(model, tile.watered)
                tile.watered = False

        self._prune()

    def _prune(self) -> None:
        """Forgets tiles and maps that hold no state, keeping saves small."""
        for map_slug in list(self._maps):
            tiles = self._maps[map_slug]
            for pos in [p for p, t in tiles.items() if t.is_empty]:
                del tiles[pos]
            if not tiles:
                del self._maps[map_slug]

    # -- persistence ----------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Prepares a dictionary of the grid to be saved."""
        self._prune()
        return {
            map_slug: {
                f"{x},{y}": tile.get_state() for (x, y), tile in tiles.items()
            }
            for map_slug, tiles in self._maps.items()
        }

    def set_state(self, save_data: dict[str, Any]) -> None:
        """Recreates the grid from saved data, discarding anything current."""
        self._maps = {}
        for map_slug, raw_tiles in (save_data or {}).items():
            tiles: dict[TilePos, FarmTile] = {}
            for raw_pos, raw_tile in raw_tiles.items():
                pos = _decode_pos(raw_pos)
                if pos is None:
                    logger.error(
                        f"Discarding farm tile with bad key '{raw_pos}' "
                        f"on map '{map_slug}'"
                    )
                    continue
                tiles[pos] = FarmTile.from_state(raw_tile)
            if tiles:
                self._maps[map_slug] = tiles


def _decode_pos(raw: str) -> TilePos | None:
    """Turns a saved ``"x,y"`` key back into a tile coordinate."""
    try:
        x, y = raw.split(",")
        return int(x), int(y)
    except ValueError:
        return None
