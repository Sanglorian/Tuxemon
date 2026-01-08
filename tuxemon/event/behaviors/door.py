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
class DoorBehavior(EventBehavior):
    name = "door"

    def expand(
        self,
        event: EventObject,
        behavior: Behavior,
    ) -> tuple[list[SpatialCondition], list[ParameterizableRule]]:
        facing, destination, x, y, direction = behavior.args

        conds = [
            SpatialCondition(
                type="char_at",
                parameters=["player"],
                box=event.box,
                operator=Operator.IS,
                name=f"{behavior.name}_at",
            ),
            SpatialCondition(
                type="char_facing",
                parameters=["player", facing],
                box=event.box,
                operator=Operator.IS,
                name=f"{behavior.name}_facing",
            ),
        ]

        acts = [
            ParameterizableRule(
                type="transition_teleport",
                parameters=[destination, x, y],
                name=f"{behavior.name}_teleport",
            ),
            ParameterizableRule(
                type="char_face",
                parameters=["player", direction],
                name=f"{behavior.name}_face",
            ),
        ]

        return conds, acts
