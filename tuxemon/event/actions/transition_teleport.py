# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.graphics import ColorLike, string_to_colorlike
from tuxemon.platform.const.graphics import BLACK_COLOR
from tuxemon.platform.const.sizes import TRANS_TIME
from tuxemon.session import Session
from tuxemon.teleporter import TeleportRequest


@final
@dataclass
class TransitionTeleportAction(EventAction):
    """
    Combines the "teleport" and "screen_transition" actions.

    Perform a teleport with a screen transition. Useful for allowing the player
    to go to different maps.

    When the player walks across a border between two maps listed in the
    world file (spyder.world), and the destination lines up with where the
    player is in world space, the screen fade is skipped so the transition
    is seamless. Doors and warps keep their fade.

    Script usage:
        .. code-block::

            transition_teleport <character>,<map_name>,<x>,<y>[,trans_time][,rgb]

    Script parameters:
        character: Slug of the character to teleport.
        map_name: Name of the map to teleport to.
        x: X coordinate of the map to teleport to.
        y: Y coordinate of the map to teleport to.
        trans_time: (Optional) Transition time in seconds. Default is 0.3.
        rgb: (Optional) Transition color in RGB format (e.g. "255:0:0" for red).
             Default is black (0,0,0).
    """

    name = "transition_teleport"
    character: str
    map_name: str
    x: int
    y: int
    trans_time: float | None = None
    rgb: str | None = None

    def start(self, session: Session) -> None:

        char = session.client.get_npc(self.character)
        if char is None:
            self.stop()
            return

        teleport_queue = session.client.teleporter.teleport_queue

        if not teleport_queue.is_empty():
            self.stop()
            return

        request = TeleportRequest(
            char=None,
            mapname=self.map_name,
            x=self.x,
            y=self.y,
            facing=None,
            source_map=char.current_map,
            source_x=char.tile_pos[0],
            source_y=char.tile_pos[1],
        )

        world_index = getattr(session.client, "world_index", None)
        source_map = char.current_map or ""
        if world_index is not None and world_index.is_seamless_link(
            source_map, char.tile_pos, self.map_name, (self.x, self.y)
        ):
            # Walking across a border between world maps: skip the fade.
            # End the step the player was taking on the old map first;
            # otherwise it carries on in the new map's coordinates and
            # can drag the player through walls.
            movement = session.client.movement_manager
            held = movement.wants_to_move_char.get(char.slug)
            char.abort_movement(preserve_position=True)
            session.client.current_music.allow_instant_switch()
            session.client.teleporter.seamless_teleport(char, request)
            if held is not None and movement.is_movement_allowed(char):
                movement.move_char(char, held)
            self.stop()
            return

        _time = TRANS_TIME if self.trans_time is None else self.trans_time
        rgb: ColorLike = BLACK_COLOR
        if self.rgb:
            rgb = string_to_colorlike(self.rgb)

        teleport_queue.enqueue(request)

        session.world.prepare_for_teleport()
        session.world.transition_manager.fade_and_teleport(
            _time,
            rgb,
            char,
            lambda: session.client.teleporter.handle_next_teleport(char),
        )

        self.stop()
