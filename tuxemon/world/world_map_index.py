# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

NATIVE_TILE = 16  # pixels per tile in the .world coordinate system


@dataclass(frozen=True)
class WorldMapEntry:
    filename: str
    world_x: int   # native-pixel x of map's top-left corner
    world_y: int   # native-pixel y of map's top-left corner
    tile_width: int
    tile_height: int

    @property
    def pixel_width(self) -> int:
        return self.tile_width * NATIVE_TILE

    @property
    def pixel_height(self) -> int:
        return self.tile_height * NATIVE_TILE


class WorldMapIndex:
    """
    Spatial index built from a Tiled .world file.

    Provides fast lookup of a map's world-space position and adjacency
    queries used for seamless multi-map rendering.
    """

    def __init__(self, world_file: Path, maps_dir: Path) -> None:
        self._maps_dir = maps_dir
        self._entries: dict[str, WorldMapEntry] = {}
        self._load(world_file)

    @classmethod
    def from_maps_dir(cls, maps_dir: Path) -> WorldMapIndex | None:
        """Load all *.world files in maps_dir and merge them into one index.

        Returns None when no world files are found.
        """
        world_files = sorted(maps_dir.glob("*.world"))
        if not world_files:
            return None

        merged: dict[str, WorldMapEntry] = {}
        for path in world_files:
            try:
                index = cls(path, maps_dir)
                merged.update(index._entries)
                logger.info(
                    f"Loaded {len(index._entries)} entries from {path.name}"
                )
            except Exception as exc:
                logger.warning(f"Failed to load world file {path}: {exc}")

        if not merged:
            return None

        instance = cls.__new__(cls)
        instance._maps_dir = maps_dir
        instance._entries = merged
        return instance

    # ------------------------------------------------------------------
    # loading

    def _load(self, world_file: Path) -> None:
        data = json.loads(world_file.read_text())
        for item in data.get("maps", []):
            filename = item["fileName"]
            tmx_path = self._maps_dir / filename

            w_px = item.get("width", 0)
            h_px = item.get("height", 0)
            if w_px == 0 or h_px == 0:
                tile_w, tile_h = self._read_tmx_tile_dims(tmx_path)
            else:
                # .world stores pixel dimensions for explicitly-sized entries
                tile_w = w_px // NATIVE_TILE
                tile_h = h_px // NATIVE_TILE

            self._entries[filename] = WorldMapEntry(
                filename=filename,
                world_x=item["x"],
                world_y=item["y"],
                tile_width=tile_w,
                tile_height=tile_h,
            )

    @staticmethod
    def _read_tmx_tile_dims(tmx_path: Path) -> tuple[int, int]:
        try:
            root = ET.parse(tmx_path).getroot()
            return int(root.get("width", 0)), int(root.get("height", 0))
        except Exception as exc:
            logger.warning(
                f"Could not read tile dims from {tmx_path.name}: {exc}"
            )
            return 0, 0

    # ------------------------------------------------------------------
    # queries

    def is_world_map(self, filename: str) -> bool:
        """True if *filename* (basename) is listed in this world index."""
        return Path(filename).name in self._entries

    def get_entry(self, filename: str) -> WorldMapEntry | None:
        """Return the entry for *filename* (basename), or None."""
        return self._entries.get(Path(filename).name)

    def get_nearby_entries(
        self,
        current_filename: str,
        viewport_native_px: tuple[int, int],
    ) -> list[WorldMapEntry]:
        """
        Return all entries whose bounds overlap the search area.

        The search area is the current map's bounding box expanded by one
        viewport in every direction — wide enough to cover anything that
        could be partially visible on screen.
        """
        current = self._entries.get(Path(current_filename).name)
        if current is None:
            return []

        vw, vh = viewport_native_px
        x0 = current.world_x - vw
        y0 = current.world_y - vh
        x1 = current.world_x + current.pixel_width + vw
        y1 = current.world_y + current.pixel_height + vh

        return [
            e
            for e in self._entries.values()
            if e.filename != current.filename
            and e.world_x < x1
            and e.world_x + e.pixel_width > x0
            and e.world_y < y1
            and e.world_y + e.pixel_height > y0
        ]