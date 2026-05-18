# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tuxemon.map.tuxemon import AbstractMap

if TYPE_CHECKING:
    from tuxemon.boundary import BoundaryChecker
    from tuxemon.event.eventengine import EventEngine
    from tuxemon.map.loader import MapLoader
    from tuxemon.map.manager import MapManager
    from tuxemon.map.tuxemon import AbstractMap
    from tuxemon.npc_manager import NPCManager
    from tuxemon.world.world_map_index import WorldMapIndex

logger = logging.getLogger(__name__)


class MapTransition:
    """Handles transitioning between maps, updating game state accordingly."""

    def __init__(
        self,
        map_loader: MapLoader,
        npc_manager: NPCManager,
        map_manager: MapManager,
        boundary: BoundaryChecker,
        event_engine: EventEngine,
    ) -> None:
        self.map_loader = map_loader
        self.map_manager = map_manager
        self.npc_manager = npc_manager
        self.boundary = boundary
        self.event_engine = event_engine
        # Set by BaseClient after construction when a world file is found.
        self.world_index: WorldMapIndex | None = None
        self._resolution: tuple[int, int] = (0, 0)
        self._scale: int = 1

    def change_map(
        self, map_name: str | None = None, yaml_path: str | None = None
    ) -> None:
        """Loads the new map or a NullMap and updates relevant game components."""
        current = self.map_manager.current_map
        self._clear_npcs()
        if map_name:
            if current is None or map_name != current.filename:
                map_data = self.map_loader.load_map_data(map_name)
            else:
                map_data = current
        else:
            map_data = self.map_loader.load_null_map(yaml_path)
        self._update_map_state(map_data)
        self._reset_events(map_data)
        self._update_boundaries()
        self._preload_adjacent_maps()

    def _preload_adjacent_maps(self) -> None:
        """Load maps adjacent to the current one and initialise their seamless renderers."""
        if not self.world_index or not self._resolution[0]:
            self.map_manager.clear_adjacent_maps()
            return

        try:
            current_name = self.map_manager.get_map_name()
        except ValueError:
            self.map_manager.clear_adjacent_maps()
            return

        if not self.world_index.is_world_map(current_name):
            self.map_manager.clear_adjacent_maps()
            return

        native_vw = self._resolution[0] // self._scale
        native_vh = self._resolution[1] // self._scale
        entries = self.world_index.get_nearby_entries(
            current_name, (native_vw, native_vh)
        )

        # Initialize seamless renderer for the current map so it can draw
        # without clamping, letting adjacent map tiles show through at edges.
        current_map = self.map_manager.current_map
        if current_map is not None:
            current_map.initialize_seamless_renderer(self._resolution)

        adjacent: list[AbstractMap] = []
        for entry in entries:
            try:
                adj_map = self.map_loader.load_map_data(entry.filename)
                adj_map.initialize_seamless_renderer(self._resolution)
                adjacent.append(adj_map)
            except Exception as exc:
                logger.warning(
                    f"Failed to preload adjacent map {entry.filename}: {exc}"
                )

        self.map_manager.set_adjacent_maps(adjacent)
        logger.debug(
            f"Preloaded {len(adjacent)} adjacent map(s) for {current_name}"
        )

    def validate_coordinates(self, x: int, y: int) -> None:
        if not self.boundary.is_within_boundaries((x, y)):
            raise ValueError(
                f"Coordinates ({x}, {y}) are out of map boundaries."
            )

    def _reset_events(self, map_data: AbstractMap) -> None:
        """Resets and updates event engine for the new map."""
        self.event_engine.reset(map_data)

    def _update_map_state(self, map_data: AbstractMap) -> None:
        """Updates the map manager with new map data."""
        self.map_manager.load_map(map_data)

    def _clear_npcs(self) -> None:
        """Clears NPCs to ensure a clean transition."""
        self.npc_manager.clear_npcs()

    def _update_boundaries(self) -> None:
        """Updates the game boundaries to fit the new map."""
        map_size = self.map_manager.map_size
        self.boundary.set_rectangular_boundary(
            "map", 0, map_size[0], 0, map_size[1]
        )
