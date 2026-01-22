# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import final

from tuxemon.db import FacingMode
from tuxemon.entity_dir.path import tile_distance
from tuxemon.event.eventaction import EventAction
from tuxemon.map.map import get_direction
from tuxemon.session import Session


@final
@dataclass
class CharFacePlayerAction(EventAction):
    """
    Make an NPC face the player when they come within a specified distance.

    Script usage:
        .. code-block::

            char_face_player <npc_slug>,<trigger_dist>,<persistent>

    Script parameters:
        npc_slug: Slug of the NPC that will track the player's facing.
        trigger_dist: Maximum tile distance at which the NPC will begin
            facing the player. Defaults to 3.
        persistent: Whether the NPC should continue tracking the player
            after the first trigger. Defaults to True.
    """

    name = "char_face_player"
    character: str
    trigger_dist: int = 3
    persistent: bool = True

    def start(self, session: Session) -> None:
        self.npc = session.get_npc(self.character)

    def update(self, session: Session, dt: float) -> None:
        if not self.npc:
            return

        dist = tile_distance(self.npc.tile_pos, session.player.tile_pos)

        if dist <= self.trigger_dist:
            # Lock facing and track the player
            self.npc.set_facing_mode(FacingMode.LOCKED)
            target_dir = get_direction(
                self.npc.tile_pos, session.player.tile_pos
            )
            self.npc.set_facing(target_dir)
        else:
            # Restore normal behavior
            self.npc.set_facing_mode(FacingMode.FOLLOW_MOVEMENT)

        if not self.persistent and dist <= self.trigger_dist:
            self.stop()
