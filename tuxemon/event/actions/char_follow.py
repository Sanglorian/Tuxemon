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
class CharFollowAction(EventAction):
    """
    Make an NPC follow a target character when they enter a trigger radius.

    Script usage:
        .. code-block::

            char_follow <follower_slug>,<target_slug>,<trigger_dist>,<min_dist>

    Script parameters:
        follower_slug: Slug of the NPC that will follow the target.
        target_slug: Slug of the NPC or player to be followed.
        trigger_dist: Maximum tile distance at which following begins.
            Defaults to 5.
        min_dist: Minimum tile distance to maintain from the target.
            When reached, the follower stops and faces the target.
            Defaults to 1.
    """

    name = "char_follow"
    follower: str
    target: str
    trigger_dist: int = 5
    min_dist: int = 1

    def start(self, session: Session) -> None:
        self.f_npc = session.get_npc(self.follower)
        self.t_npc = session.get_npc(self.target)

    def update(self, session: Session, dt: float) -> None:
        if not self.f_npc or not self.t_npc:
            return

        dist = tile_distance(self.f_npc.tile_pos, self.t_npc.tile_pos)

        # Start following
        if dist <= self.trigger_dist and dist > self.min_dist:
            self.f_npc.set_facing_mode(FacingMode.FOLLOW_MOVEMENT)
            if not self.f_npc.moving:
                self.f_npc.path_controller.start_path(self.t_npc.tile_pos)

        # Stop and face target
        elif dist <= self.min_dist:
            self.f_npc.path_controller.cancel_path()
            self.f_npc.set_facing_mode(FacingMode.LOCKED)
            self.f_npc.set_facing(
                get_direction(self.f_npc.tile_pos, self.t_npc.tile_pos)
            )
