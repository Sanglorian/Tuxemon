# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING, Generic, Optional, TypeVar
from uuid import UUID, uuid4

from tuxemon.db import Direction
from tuxemon.map.map import dirs2
from tuxemon.math import Vector2
from tuxemon.tools import vector2_to_tile_pos
from tuxemon.user_config import CONFIG

if TYPE_CHECKING:
    from tuxemon.session import Session


SaveDict = TypeVar("SaveDict")


class EntityState(Enum):
    IDLE = "idle"
    WALKING = "walking"
    RUNNING = "running"
    JUMPING = "jumping"


class Body:
    """
    Handles 2D movement of an entity.
    """

    def __init__(
        self,
        position: Vector2,
        velocity: Optional[Vector2] = None,
        acceleration: Optional[Vector2] = None,
    ) -> None:
        self.position = position
        self.velocity = velocity or Vector2(0, 0)
        self.acceleration = acceleration or Vector2(0, 0)

    @property
    def is_moving(self) -> bool:
        """Returns whether the entity is currently moving."""
        return self.velocity != Vector2(0, 0)

    def update(self, time_delta: float) -> None:
        """
        Updates the position based on velocity and time.
        """
        self.velocity += self.acceleration * time_delta
        self.position += self.velocity * time_delta

    def reset(
        self,
        reset_position: bool = True,
        reset_velocity: bool = True,
        reset_acceleration: bool = True,
    ) -> None:
        """
        Resets attributes selectively.
        """
        if reset_position:
            self.position = Vector2(0, 0)
        if reset_velocity:
            self.velocity = Vector2(0, 0)
        if reset_acceleration:
            self.acceleration = Vector2(0, 0)


class Mover:
    """
    Handles movement state transitions and movement logic.
    """

    def __init__(
        self,
        body: Body,
        facing: Direction = Direction.down,
        base_moverate: float = CONFIG.player_walkrate,
        moverate_modifier: float = 1.0,
    ) -> None:
        self.state = EntityState.IDLE
        self.body = body
        self.facing = facing
        self.base_moverate = base_moverate
        self.moverate_modifier = moverate_modifier
        self.move_direction: Optional[Direction] = None

    @property
    def moverate(self) -> float:
        return self.base_moverate * self.moverate_modifier

    @property
    def is_moving_state(self) -> bool:
        return self.state in (
            EntityState.WALKING,
            EntityState.RUNNING,
            EntityState.JUMPING,
        )

    def move(self, direction: Direction) -> None:
        """Applies movement in a given direction."""
        direction_vector = dirs2[direction]  # 2D direction table
        self.body.velocity = direction_vector * self.moverate
        self.facing = direction

        new_state = (
            EntityState.RUNNING
            if self.base_moverate == CONFIG.player_runrate
            else EntityState.WALKING
        )
        self.set_state(new_state)

    def stop(self) -> None:
        """Stops movement and transitions to IDLE."""
        self.body.velocity = Vector2(0, 0)
        self.set_state(EntityState.IDLE)

    def running(self) -> None:
        """Boosts moverate to running speed."""
        if self.body.is_moving:
            self.base_moverate = CONFIG.player_runrate
            self.set_state(EntityState.RUNNING)

    def walking(self) -> None:
        """Resets moverate back to walking speed."""
        if self.body.is_moving:
            self.base_moverate = CONFIG.player_walkrate
            self.set_state(EntityState.WALKING)

    def jump(self) -> None:
        """Triggers a jump animation state."""
        if self.state != EntityState.JUMPING:
            self.set_state(EntityState.JUMPING)

    def set_state(self, new_state: EntityState) -> None:
        """
        Controls the entity's state transitions.
        """
        if self.state == new_state:
            return

        # Reset movement when going idle
        if new_state == EntityState.IDLE:
            self.body.velocity = Vector2(0, 0)
            self.base_moverate = CONFIG.player_walkrate

        self.state = new_state

    def update_movement_state(self, running: bool) -> None:
        """
        Updates movement state based on whether the player is running
        or walking.
        """
        if self.body.is_moving:
            if running:
                self.running()
            else:
                self.walking()
        else:
            self.stop()


class Entity(Generic[SaveDict]):
    """
    Entity in the game.

    Eventually a class for all things that exist on the
    game map, like NPCs, players, objects, etc.

    Need to refactor in most NPC code to here.
    Need to refactor -out- all drawing/sprite code.
    """

    def __init__(
        self,
        *,
        slug: str = "",
        session: Session,
    ) -> None:
        self.slug = slug
        self.session = session
        self.client = session.client
        self.instance_id: UUID = uuid4()
        self.body = Body(position=Vector2(0, 0))
        self.mover = Mover(self.body)
        self._current_map: Optional[str] = None
        self.update_location: bool = False
        self.is_player: bool = False
        self.ignore_collisions: bool = False

    # === PHYSICS START =======================================================
    def stop_moving(self) -> None:
        """Completely stop all movement."""
        self.mover.stop()

    def pos_update(self) -> None:
        """WIP.  Required to be called after position changes."""
        self.network_notify_location_change()

    def network_notify_start_moving(self, direction: Direction) -> None:
        r"""WIP guesswork ¯\_(ツ)_/¯"""
        self.network = self.client.network_manager
        if self.network.is_connected():
            assert self.network.client
            self.network.client.update_player(
                direction, event_type="CLIENT_MOVE_START"
            )

    def network_notify_stop_moving(self) -> None:
        r"""WIP guesswork ¯\_(ツ)_/¯"""
        self.network = self.client.network_manager
        if self.network.is_connected():
            assert self.network.client
            self.network.client.update_player(
                self.facing, event_type="CLIENT_MOVE_COMPLETE"
            )

    def network_notify_location_change(self) -> None:
        r"""WIP guesswork ¯\_(ツ)_/¯"""
        self.update_location = True

    def update_physics(self, td: float) -> None:
        """
        Move the entity according to the movement vector.

        Parameters:
            td: Time delta (elapsed time).
        """
        self.body.update(td)
        self.pos_update()

    def set_position(self, pos: Sequence[float]) -> None:
        """
        Set the entity's position in the game world.

        Parameters:
            pos: Position to be set.
        """
        self.body.position = Vector2(*pos)
        self.add_collision(pos)
        self.pos_update()

    def set_current_map(self, map_slug: Optional[str]) -> None:
        """
        Set the entity's map in the game world.

        Parameters:
            map_slug: Map to be set.
        """
        self._current_map = map_slug

    def set_moverate(self, moverate: float) -> None:
        """
        Sets the entity's movement rate.

        Parameters:
            moverate: The new movement rate to be applied.
        """
        self.mover.base_moverate = moverate

    def set_moverate_modifier(self, modifier: float) -> None:
        """Sets a new moverate modifier.

        Parameters:
            modifier: The new modifier to be applied.
        """
        self.mover.moverate_modifier = max(0.0, modifier)

    def set_facing(self, direction: Direction) -> None:
        """
        Sets the entity's facing direction.

        Parameters:
            direction: The new direction the entity will face.
        """
        self.mover.facing = direction

    def set_move_direction(
        self, direction: Optional[Direction] = None
    ) -> None:
        """
        Sets the move direction of the entity.

        Parameters:
            direction: The new direction the entity will face.
        """
        self.mover.move_direction = direction

    def add_collision(self, pos: Sequence[float]) -> None:
        """
        Set the entity's wandering position in the collision zone.
        """
        self.client.collision_manager.add_collision(self, pos)

    def remove_collision(self) -> None:
        """
        Remove the entity's wandering position from the collision zone.
        """
        self.client.collision_manager.remove_collision(self.tile_pos)

    # === PHYSICS END =========================================================

    @property
    def tile_pos(self) -> tuple[int, int]:
        """Return the tile position of the entity."""
        return vector2_to_tile_pos(self.body.position)

    @property
    def current_map(self) -> Optional[str]:
        """Return the current map of the entity."""
        return self._current_map

    @property
    def position(self) -> Vector2:
        """Return the current position of the entity."""
        return self.body.position

    @property
    def velocity(self) -> Vector2:
        """Return the current velocity of the entity."""
        return self.body.velocity

    @property
    def moverate(self) -> float:
        """Returns the moverate."""
        return self.mover.moverate

    @property
    def moving(self) -> bool:
        """Return ``True`` if the entity is moving."""
        return self.body.is_moving

    @property
    def facing(self) -> Direction:
        return self.mover.facing

    @property
    def move_direction(self) -> Optional[Direction]:
        """
        Move direction allows other functions to move the entity in a
        controlled way. To move the entity, change the value to one of
        four directions: left, right, up or down. The entity will then
        move one tile in that direction until it is set to None.
        """
        return self.mover.move_direction

    def jump(self) -> None:
        """Triggers a jump for the entity."""
        self.mover.jump()

    def get_state(self, session: Session) -> SaveDict:
        """
        Get Entities internal state for saving/loading.

        Parameters:
            session: Game session.
        """
        raise NotImplementedError

    def set_state(
        self,
        session: Session,
        save_data: SaveDict,
    ) -> None:
        """
        Recreates entity from saved data.

        Parameters:
            session: Game session.
            save_data: Data used to recreate the Entity.
        """
        raise NotImplementedError
