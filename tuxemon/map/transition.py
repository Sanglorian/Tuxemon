# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

from tuxemon.map.loader import MapLoader
from tuxemon.map.tuxemon import AbstractMap

if TYPE_CHECKING:
    from tuxemon.boundary import BoundaryChecker
    from tuxemon.event.eventengine import EventEngine
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
        self._wanted_adjacent: set[str] = set()
        self._loading: dict[str, Future[AbstractMap]] = {}
        self._executor: ThreadPoolExecutor | None = None
        self._background_loader: MapLoader | None = None

    def change_map(
        self, map_name: str | None = None, yaml_path: str | None = None
    ) -> None:
        """Loads the new map or a NullMap and updates relevant game components."""
        current = self.map_manager.current_map
        self._clear_npcs()
        if map_name:
            if current is None or map_name != current.filename:
                map_data = self._take_background_load(
                    map_name
                ) or self.map_loader.load_map_data(map_name)
            else:
                map_data = current
        else:
            map_data = self.map_loader.load_null_map(yaml_path)
        self._update_map_state(map_data)
        self._reset_events(map_data)
        self._update_boundaries()
        self._clear_overlay()
        self._preload_adjacent_maps()

    def _clear_overlay(self) -> None:
        """Reset the world overlay so it does not persist across maps.

        Each map re-asserts its own overlay (e.g. the torchlight in a
        dungeon or the night tint outdoors) through its events, so the
        previous map's overlay must not bleed through.
        """
        try:
            renderer = self.event_engine.session.client.map_renderer
        except ValueError:
            return
        renderer.clear_overlay()

    def _preload_adjacent_maps(self) -> None:
        """Queue the maps bordering the current one for seamless rendering.

        Only maps that touch the current map in the world file are used,
        and any not already cached are loaded on a background thread (see
        :meth:`load_pending_adjacent`) so crossing a border never stalls.
        """
        self._wanted_adjacent = set()
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

        # The current map draws without clamping so neighbouring maps can
        # show through at its edges. Reuse the renderer if the map came
        # from the cache with one already built.
        current_map = self.map_manager.current_map
        if current_map is not None and current_map.seamless_renderer is None:
            current_map.initialize_seamless_renderer(self._resolution)

        wanted = {
            entry.filename
            for entry in self.world_index.get_touching_entries(current_name)
        }
        self._wanted_adjacent = wanted
        adjacent: list[AbstractMap] = []
        for filename in sorted(wanted):
            cached = self.map_loader.peek_cached(filename)
            if cached is not None and cached is not current_map:
                if cached.seamless_renderer is None:
                    cached.initialize_seamless_renderer(self._resolution)
                adjacent.append(cached)
            elif cached is None and filename not in self._loading:
                self._loading[filename] = self._get_executor().submit(
                    self._load_in_background, filename
                )
        self.map_manager.set_adjacent_maps(adjacent)
        logger.debug(
            f"{current_name}: {len(adjacent)} adjacent map(s) ready, "
            f"{len(self._loading)} loading"
        )

    def _get_executor(self) -> ThreadPoolExecutor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="adjacent-maps"
            )
            # A separate, uncached loader: the main loader's cache is only
            # ever touched from the main thread.
            self._background_loader = MapLoader(
                self.map_loader.context, enable_cache=False
            )
        return self._executor

    def _load_in_background(self, filename: str) -> AbstractMap:
        """Runs on the worker thread: parse the map and build its renderer."""
        assert self._background_loader is not None
        adj_map = self._background_loader.load_map_data(filename)
        adj_map.initialize_seamless_renderer(self._resolution)
        return adj_map

    def _take_background_load(self, map_name: str) -> AbstractMap | None:
        """
        If *map_name* is being loaded in the background and isn't cached,
        wait for that load rather than starting a second one from scratch.
        """
        future = self._loading.get(Path(map_name).name)
        if future is None or self.map_loader.peek_cached(map_name):
            return None
        del self._loading[Path(map_name).name]
        try:
            map_data = future.result()
        except Exception as exc:
            logger.warning(f"Background load of {map_name} failed: {exc}")
            return None
        self.map_loader.add_to_cache(map_data.filename, map_data)
        return map_data

    def load_pending_adjacent(self) -> None:
        """Collect adjacent maps finished in the background. Call per frame."""
        if not self._loading:
            return
        current_map = self.map_manager.current_map
        for filename, future in list(self._loading.items()):
            if not future.done():
                continue
            del self._loading[filename]
            try:
                adj_map = future.result()
            except Exception as exc:
                logger.warning(
                    f"Failed to preload adjacent map {filename}: {exc}"
                )
                continue
            # If the main thread loaded this map itself in the meantime (the
            # player crossed before we finished), keep that copy.
            existing = self.map_loader.peek_cached(filename)
            if existing is not None:
                adj_map = existing
                if adj_map.seamless_renderer is None:
                    adj_map.initialize_seamless_renderer(self._resolution)
            else:
                self.map_loader.add_to_cache(adj_map.filename, adj_map)
            if (
                filename in self._wanted_adjacent
                and adj_map is not current_map
                and adj_map not in self.map_manager.adjacent_maps
            ):
                self.map_manager.set_adjacent_maps(
                    [*self.map_manager.adjacent_maps, adj_map]
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
