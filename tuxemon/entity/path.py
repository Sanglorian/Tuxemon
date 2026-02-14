# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from math import hypot
from typing import TYPE_CHECKING

from tuxemon.db import Direction, FacingMode
from tuxemon.map.map import dirs2, get_direction
from tuxemon.math import Vector2
from tuxemon.tools import vector2_to_tile_pos

if TYPE_CHECKING:
    from tuxemon.entity.npc import NPC
    from tuxemon.map.manager import MapManager
    from tuxemon.movement import Pathfinder
    from tuxemon.npc_manager import NPCManager


logger = logging.getLogger(__name__)


def tile_distance(tile0: Iterable[float], tile1: Iterable[float]) -> float:
    x0, y0 = tile0
    x1, y1 = tile1
    return hypot(x1 - x0, y1 - y0)


class PathView:
    """
    A contributor-proof path abstraction.

    Invariant:
        - The NEXT waypoint is always the LAST element of _tiles.
        - Path grows toward the front; consumption pops from the end.
    """

    __slots__ = ("_tiles", "_consumed")

    def __init__(self, tiles: Iterable[tuple[int, int]]):
        self._tiles = list(tiles)
        self._consumed: list[tuple[int, int]] = []

    def next(self) -> tuple[int, int] | None:
        """Return the next waypoint without consuming it."""
        return self._tiles[-1] if self._tiles else None

    def consume(self) -> tuple[int, int] | None:
        """Consume and return the next waypoint."""
        if not self._tiles:
            return None
        tile = self._tiles.pop()
        self._consumed.append(tile)
        return tile

    def push(self, tile: tuple[int, int]) -> None:
        """Append a new waypoint as the next step."""
        self._tiles.append(tile)

    def prepend(self, tile: tuple[int, int]) -> None:
        """
        Insert a waypoint at the *start* of the path.
        This is used for dynamic rerouting.
        """
        self._tiles.insert(0, tile)

    def extend_reversed(self, tiles: Iterable[tuple[int, int]]) -> None:
        """Append a reversed sequence so the last element is the next waypoint."""
        seq = list(tiles)
        self._tiles.extend(reversed(seq))

    def peek(self, n: int = 0) -> tuple[int, int] | None:
        """
        Peek n steps ahead.
        n=0 → next waypoint
        n=1 → second next waypoint
        """
        idx = len(self._tiles) - 1 - n
        if idx < 0:
            return None
        return self._tiles[idx]

    def clear(self) -> None:
        """Remove all remaining waypoints."""
        self._tiles.clear()

    def replace_tail(self, tiles: Iterable[tuple[int, int]]) -> None:
        """Replace the remaining path with a new sequence."""
        self._tiles = list(tiles)

    def splice(self, tiles: Iterable[tuple[int, int]]) -> None:
        """
        Insert new waypoints so they become the next steps.
        Equivalent to replacing the tail but preserving the invariant.
        """
        seq = list(tiles)
        self._tiles.extend(reversed(seq))

    def to_list(self) -> list[tuple[int, int]]:
        """Return a copy of the path."""
        return list(self._tiles)

    def consumed(self) -> list[tuple[int, int]]:
        """Return consumed waypoints (debug only)."""
        return list(self._consumed)

    def __len__(self) -> int:
        return len(self._tiles)

    def __bool__(self) -> bool:
        return bool(self._tiles)

    def __iter__(self) -> Iterator[tuple[int, int]]:
        return iter(self._tiles)

    def __repr__(self) -> str:
        return f"PathView(next={self.next()}, len={len(self)})"


@dataclass
class PathExecutionState:
    """
    Tracks a single tile-to-tile movement transition.
    """

    origin: tuple[int, int] | None = None
    target: tuple[int, int] | None = None

    @property
    def in_progress(self) -> bool:
        return self.origin is not None and self.target is not None

    def reset(self) -> None:
        self.origin = None
        self.target = None


class PathController:
    def __init__(
        self,
        owner: NPC,
        pathfinder: Pathfinder,
        map_manager: MapManager,
        npc_manager: NPCManager,
    ) -> None:
        self.owner = owner
        self._pathfinder = pathfinder
        self._map_manager = map_manager
        self._npc_manager = npc_manager

        self.path = PathView([])
        self._repath_cooldown: float = 0.0
        self.pathfinding: tuple[int, int] | None = None
        self.exec = PathExecutionState()

    @property
    def move_destination(self) -> tuple[int, int] | None:
        """Only used for the char_moved condition."""
        return self.path.next()

    def start_path(self, destination: tuple[int, int]) -> None:
        """
        Find a path and also start it.

        If asked to pathfind, an NPC will pathfind until it:
        * reaches the destination
        * NPC.cancel_movement() is called

        If blocked, the NPC will wait until it is able to move.

        Queries the world for a valid path.

        Parameters:
            destination: Desired final position.
        """
        self.pathfinding = destination
        path = self._pathfinder.pathfind(
            self.owner.tile_pos, destination, self.owner.facing
        )
        if path:
            self.path = PathView(path)
            self.next_waypoint()
        else:
            # If pathfinding fails, ensure all path data is cleared.
            self.cancel_path()
            logger.warning(
                f"Could not find path for {self.owner.slug} from "
                f"{self.owner.tile_pos} to {destination}."
            )

    def update(self, time_delta: float) -> None:
        self._repath_cooldown = max(0.0, self._repath_cooldown - time_delta)

        if self.path or self.owner.move_direction:
            self.process_movement()

    def process_movement(self) -> None:
        """
        Manages NPC movement logic, handling pathfinding, waypoint progression,
        and obstructions.

        This method ensures smooth movement by:
        - Initiating pathfinding if needed.
        - Progressing through waypoints.
        - Responding to blocked paths or missing destinations.
        - Handling direct movement requests when no path exists.

        If movement is blocked or invalid, appropriate cancellation routines
        are triggered.
        """
        if self.pathfinding and not self.path:
            if self._repath_cooldown <= 0.0:
                self.start_path(self.pathfinding)
            return

        if self.path:
            if self.exec.in_progress:
                self.check_waypoint()
            else:
                self.next_waypoint()

        # Direct movement handling
        if self.owner.move_direction:
            if self.path and not self.owner.moving:
                self.cancel_path()

            if not self.path:
                self.move_one_tile(self.owner.move_direction)
                self.next_waypoint()

        if not self.path:
            self.cancel_movement()
            self.owner.sprite_controller.stop_animation()

    def set_path_and_start(self, path: list[tuple[int, int]]) -> None:
        """
        Assigns a new path to the controller and initiates movement toward the first waypoint.
        """
        self.path = PathView(path)
        logger.debug(f"Path set for {self.owner.slug}: {self.path}")
        self.next_waypoint()

    def next_waypoint(self) -> None:
        """
        Take the next step of the path, stop if way is blocked.

        * This must be called after a path is set
        * Not needed to be called if existing path is modified
        * If the next waypoint is blocked, the waypoint will be removed
        """
        if not self.path:
            return

        target = self.path.next()
        assert target is not None
        move_dir = get_direction(self.owner.tile_pos, target)
        if self.owner.facing_mode == FacingMode.FOLLOW_MOVEMENT:
            direction = get_direction(self.owner.position, target)
            self.owner.set_facing(direction)

        try:
            if self._pathfinder.is_tile_traversable(
                self.owner.tile_pos,
                self.owner.facing,
                target,
                self.owner.ignore_collisions,
            ):
                # Surfanim suffers from significant clock drift, causing
                # timing inconsistencies. Even after completing one animation
                # cycle, the timing can become inaccurate. This drift results
                # in walking steps misaligning with tile positions, with
                # certain frames lasting only a single game frame.
                # Using `play` to initiate each tile transition helps reset
                # the surfanim timer, keeping walking animation frames in sync.
                # However, occasional desynchronization still occurs.
                # To fully resolve this issue, the game will eventually need
                # a dedicated global clock—not reliant on wall time—to eliminate
                # visual glitches and ensure frame accuracy.
                self.owner.sprite_controller.play_animation(move_dir)
                self.exec.origin = self.owner.tile_pos
                self.exec.target = target
                self.owner.mover.move(move_dir)
                self.owner.remove_collision()
            else:
                self.owner.stop_moving()
                self.handle_obstruction(target)
        except Exception as e:
            logger.error(
                f"Error in next_waypoint for {self.owner.slug}: {e}",
                exc_info=True,
            )
            self.cancel_path()

    def check_waypoint(self) -> None:
        """
        Check if the waypoint is reached and sets new waypoint if so.

        * For most accurate speed, tests distance traveled.
        * Doesn't verify the target position, just distance
        * Assumes once waypoint is set, direction doesn't change
        * Honors continue tiles
        """
        if not self.exec.in_progress:
            return

        origin = self.exec.origin
        target = self.exec.target
        assert origin is not None and target is not None

        expected = tile_distance(origin, target)
        traveled = tile_distance(self.owner.position, origin)
        if traveled >= expected:
            self.owner.set_position(target)
            self.owner.on_tile_changed()
            self.path.consume()
            self.exec.reset()
            self._apply_tile_effects()
            self.check_continue()
            if self.path:
                self.next_waypoint()

    def check_continue(self) -> None:
        try:
            tile = self._map_manager.collision_map[self.owner.tile_pos]
            if tile and tile.endure:
                # Use self.owner.facing if the tile allows multiple directions (> 1).
                if len(tile.endure) > 1:
                    _direction = self.owner.facing
                # Otherwise, it must be the single required direction (len == 1).
                else:
                    _direction = tile.endure[0]

                self.move_one_tile(_direction)
            else:
                pass
        except (KeyError, TypeError):
            pass

    def _apply_tile_effects(self) -> None:
        try:
            tile = self._map_manager.collision_map.get(self.owner.tile_pos)
            if tile is None:
                return

            if tile.push_effect:
                self.move_multiple_tiles(
                    direction=tile.push_effect.direction,
                    strength=tile.push_effect.strength,
                )

            if tile.speed_modifier:
                self.owner.set_moverate_modifier(tile.speed_modifier)
        except (KeyError, TypeError):
            pass

    def _get_next_tile_pos(
        self, origin: tuple[int, int], direction: Direction
    ) -> tuple[int, int]:
        """Calculates the target tile position one step away from the origin."""
        target_vec = Vector2(origin) + dirs2[direction]
        return vector2_to_tile_pos(target_vec)

    def move_one_tile(self, direction: Direction) -> None:
        target = self._get_next_tile_pos(self.owner.tile_pos, direction)
        self.path.push(target)

    def move_multiple_tiles(self, direction: Direction, strength: int) -> None:
        """
        Attempts to move the entity multiple tiles in the specified direction,
        up to the given strength.

        This method checks tile-by-tile whether movement is allowed using the
        pathfinder's exit logic.
        If a tile is blocked, movement stops at the last valid position. The
        resulting path is reversed before being appended to ensure that the
        next waypoint is always the immediate neighbor, since movement logic
        expects self.path.next() to be adjacent to the current position.

        Parameters:
            direction: The direction in which to move.
            strength: The maximum number of tiles to attempt moving through.
        """
        if strength <= 0:
            return

        if self.owner.facing_mode == FacingMode.FOLLOW_MOVEMENT:
            self.owner.set_facing(direction)

        origin = self.path.next()
        if origin is None:
            origin = self.owner.tile_pos
        steps: list[tuple[int, int]] = []

        for _ in range(strength):
            candidate = self._get_next_tile_pos(origin, direction)

            if candidate == origin:
                logger.debug(f"Skipping duplicate tile: {candidate}")
                continue

            exits = self._pathfinder.get_exits(origin, direction)
            logger.debug(
                f"Valid exits from {origin} facing {direction}: {exits}"
            )
            if candidate not in exits:
                logger.debug(
                    f"Tile blocked: {candidate} from {origin} facing {direction}"
                )
                break

            steps.append(candidate)
            origin = candidate

        if steps:
            self.path.extend_reversed(steps)
            self.exec.origin = self.owner.tile_pos
            logger.debug(
                f"Final path (last is next): {self.path} | origin={self.exec.origin}"
            )
            self.next_waypoint()

    def cancel_path(self) -> None:
        """
        Clears all active pathfinding data and stops the NPC's movement.

        This method removes the NPC's current path and resets pathfinding
        related attributes, ensuring no further automatic movement occurs.
        """
        self.path = PathView([])
        self.pathfinding = None
        self.exec.reset()

    def cancel_movement(self) -> None:
        """
        Stops the NPC's movement and adjusts pathfinding logic if necessary.

        If the NPC is currently following a path but hasn't reached the
        destination, it retains the last waypoint to avoid abrupt stopping.
        Otherwise, all movement is halted and pathfinding is cleared.
        """
        at_origin = (
            self.exec.origin is not None
            and self.owner.position == self.exec.origin
        )
        mid_movement = self.path and self.owner.moving

        if at_origin:
            # Movement started but hasn't progressed
            self.abort_movement(preserve_position=True)
            return

        if mid_movement:
            # Keep last waypoint so NPC finishes the tile cleanly
            last = self.path.next()
            self.path = PathView([last] if last else [])
            self.pathfinding = None
            self.owner.set_move_direction()
            return

        # Default: fully stop and clear everything
        self.abort_movement()

    def abort_movement(self, preserve_position: bool = False) -> None:
        """
        Safely halts all movement-related actions for the NPC.

        This method ensures that the NPC stops moving, cancels any
        active pathfinding, and resets its movement direction. If
        `preserve_position` is True, the NPC's current tile position
        is retained; otherwise, it reverts to its last recorded origin.
        """
        if not preserve_position and self.exec.origin is not None:
            self.owner.set_position(self.exec.origin)
            self.owner.on_tile_changed()
        self.owner.set_move_direction()
        self.owner.stop_moving()
        self.cancel_path()

    def handle_obstruction(self, target: tuple[int, int]) -> None:
        if self.pathfinding:
            npc = self._npc_manager.get_entity_pos(self.pathfinding)
            if npc:
                logger.info(
                    f"{npc.slug} obstructing {self.owner.slug}, recalculating path."
                )
                self._repath_cooldown = 0.5
                self.start_path(self.pathfinding)
            else:
                logger.warning(
                    f"{self.owner.slug} could not proceed to {self.pathfinding} due to obstruction. "
                    "Consider splitting pathfinding or postponing movement."
                )
                self._repath_cooldown = 1.0
                self.owner.stop_moving()
        else:
            logger.debug(
                f"{self.owner.slug} faced obstruction at {target}. Movement stopped."
            )
