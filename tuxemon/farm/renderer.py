# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

from pygame.rect import Rect
from pygame.surface import Surface

from tuxemon.graphics import slice_spritesheet_surface
from tuxemon.map.map import get_pos_from_tilepos
from tuxemon.math import Vector2
from tuxemon.platform.const.sizes import TILE_SIZE
from tuxemon.prepare import DISPLAY_CONTEXT, DisplayContext

if TYPE_CHECKING:
    from tuxemon.farm.crop import CropModel
    from tuxemon.farm.grid import FarmTile, TilePos
    from tuxemon.farm.manager import FarmManager
    from tuxemon.map.manager import MapManager
    from tuxemon.map.tuxemon import AbstractMap

logger = logging.getLogger(__name__)

SOIL_SPRITE: Final[str] = "sprites/crops/soil.png"
SOIL_DRY: Final[int] = 0
SOIL_WET: Final[int] = 1

# Soil and crops draw beneath the layer characters stand on, so the player
# always walks in front of the plants rather than being hidden behind them.
SOIL_LAYER_OFFSET: Final[int] = 2
CROP_LAYER_OFFSET: Final[int] = 1


class CropSpriteCache:
    """
    Loads and caches the sprite frames for soil and for each crop.

    A missing or malformed sheet is logged and then remembered as "no
    frames", so bad art degrades into an invisible crop instead of taking
    the render loop down with it, and without hitting the disk every frame.
    """

    def __init__(self) -> None:
        self._frames: dict[str, list[Surface]] = {}

    def get_soil_frames(self, scale: int) -> list[Surface]:
        """Frames for bare tilled soil: dry first, watered second."""
        return self._load(SOIL_SPRITE, "soil", *TILE_SIZE, scale)

    def get_crop_frames(self, model: CropModel, scale: int) -> list[Surface]:
        """
        Frames for one crop: youngest growth stage first, mature last, and
        optionally a withered frame after that.
        """
        return self._load(
            model.sprite,
            model.slug,
            model.frame_width or TILE_SIZE[0],
            model.frame_height or TILE_SIZE[1],
            scale,
        )

    def set_frames(self, key: str, frames: list[Surface]) -> None:
        """Supplies frames directly, bypassing the loader."""
        self._frames[key] = frames

    def clear(self) -> None:
        """Drops cached frames, e.g. after a resolution change."""
        self._frames.clear()

    def _load(
        self,
        path: str,
        key: str,
        frame_width: int,
        frame_height: int,
        scale: int,
    ) -> list[Surface]:
        if key in self._frames:
            return self._frames[key]

        frames: list[Surface] = []
        try:
            # Imported here rather than at module scope: tuxemon.map.view
            # type-checks against CropLayer, and importing it up top would
            # close that loop into a real import cycle.
            from tuxemon.map.view import load_and_scale_with_cache

            sheet = load_and_scale_with_cache(path)
            frames = slice_spritesheet_surface(
                sheet, frame_width * scale, frame_height * scale
            )
        except Exception as e:
            logger.error(f"Could not load crop sheet '{path}' for {key}: {e}")

        self._frames[key] = frames
        return frames


class CropLayer:
    """
    Draws the farm grid: tilled soil, and the crops growing on it.

    The layer produces positioned screen surfaces in the shape the map
    renderer already hands to pyscroll — ``(surface, rect, layer)`` — so
    crops interleave with map tiles and characters rather than being pasted
    over the finished frame.
    """

    def __init__(
        self,
        farm_manager: FarmManager,
        map_manager: MapManager,
        context: DisplayContext = DISPLAY_CONTEXT,
        sprites: CropSpriteCache | None = None,
    ) -> None:
        self.farm_manager = farm_manager
        self.map_manager = map_manager
        self.context = context
        self.sprites = sprites if sprites is not None else CropSpriteCache()

    def get_rendered_tiles(
        self, current_map: AbstractMap
    ) -> list[tuple[Surface, Rect, int]]:
        """
        Returns every soil and crop surface visible on the current map,
        positioned in screen coordinates.
        """
        map_slug = self.map_manager.map_slug
        if not map_slug:
            return []

        # Tile positions are resolved against the map renderer's centre
        # offset. MapRenderer.draw initialises that before asking for these
        # surfaces, but a caller outside the draw path may not have.
        if current_map.renderer is None:
            return []

        soil_layer, crop_layer = self._layers(current_map.sprite_layer)
        rendered: list[tuple[Surface, Rect, int]] = []

        for pos, tile in self.farm_manager.grid.tiles(map_slug):
            rendered.extend(
                self._render_tile(
                    current_map, pos, tile, soil_layer, crop_layer
                )
            )

        return rendered

    @staticmethod
    def _layers(sprite_layer: int) -> tuple[int, int]:
        """
        Picks the map layers soil and crops draw on. Both sit below the layer
        characters occupy, so the player is never hidden behind a plant.
        """
        return (
            max(0, sprite_layer - SOIL_LAYER_OFFSET),
            max(0, sprite_layer - CROP_LAYER_OFFSET),
        )

    def _render_tile(
        self,
        current_map: AbstractMap,
        pos: TilePos,
        tile: FarmTile,
        soil_layer: int,
        crop_layer: int,
    ) -> list[tuple[Surface, Rect, int]]:
        rendered: list[tuple[Surface, Rect, int]] = []

        if tile.tilled:
            soil = self._pick_soil_frame(tile)
            if soil is not None:
                placed = self._place(current_map, pos, soil)
                if placed is not None:
                    rendered.append((soil, placed, soil_layer))

        crop_frame = self._pick_crop_frame(tile)
        if crop_frame is not None:
            placed = self._place(current_map, pos, crop_frame)
            if placed is not None:
                rendered.append((crop_frame, placed, crop_layer))

        return rendered

    def _pick_soil_frame(self, tile: FarmTile) -> Surface | None:
        frames = self.sprites.get_soil_frames(self.context.scale)
        if not frames:
            return None
        index = SOIL_WET if tile.watered else SOIL_DRY
        return frames[index] if index < len(frames) else frames[-1]

    def _pick_crop_frame(self, tile: FarmTile) -> Surface | None:
        if tile.crop is None:
            return None

        model = tile.crop.model
        if model is None:
            return None

        frames = self.sprites.get_crop_frames(model, self.context.scale)
        if not frames:
            return None

        index = tile.crop.get_stage(model).index
        if index >= len(frames):
            logger.warning(
                f"Crop '{model.slug}' has {len(frames)} frames but needs "
                f"frame {index}; drawing the last one instead"
            )
            index = len(frames) - 1
        return frames[index]

    def _place(
        self, current_map: AbstractMap, pos: TilePos, frame: Surface
    ) -> Rect | None:
        """
        Positions a frame on its tile, anchored to the bottom of the tile so
        that sprites taller than one tile grow upwards out of the soil.

        Returns ``None`` when the tile is off-screen.
        """
        x, y = get_pos_from_tilepos(current_map, self.context, Vector2(pos))
        tile_width, tile_height = self.context.tile_size

        rect = Rect((0, 0), frame.get_size())
        rect.centerx = x + tile_width // 2
        rect.bottom = y + tile_height

        return rect if rect.colliderect(self.context.rect) else None
