# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass

from tuxemon.db import (
    Behavior,
    EventObject,
    Operator,
    ParameterizableRule,
    SpatialCondition,
)
from tuxemon.event.eventbehavior import EventBehavior


@dataclass
class TalkBehavior(EventBehavior):
    name = "talk"

    def expand(
        self,
        event: EventObject,
        behavior: Behavior,
    ) -> tuple[list[SpatialCondition], list[ParameterizableRule]]:
        npc = behavior.args[0]

        conds = [
            SpatialCondition(
                type="char_facing_char",
                parameters=["player", npc],
                box=event.box,
                operator=Operator.IS,
                name=f"{behavior.name}_facing",
            ),
            SpatialCondition(
                type="button_pressed",
                parameters=["INTERACT"],
                box=event.box,
                operator=Operator.IS,
                name=f"{behavior.name}_interact",
            ),
        ]

        acts = [
            ParameterizableRule(
                type="char_face",
                parameters=[npc, "player"],
                name=f"{behavior.name}_face",
            )
        ]

        return conds, acts
