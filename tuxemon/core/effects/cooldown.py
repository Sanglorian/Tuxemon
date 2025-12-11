# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, TechEffectResult
from tuxemon.event.conditions.common import CommonCondition
from tuxemon.prepare import RECHARGE_RANGE

if TYPE_CHECKING:
    from tuxemon.monster import Monster
    from tuxemon.session import Session
    from tuxemon.technique.technique import Technique


@dataclass
class CoolDownEffect(CoreEffect):
    """
    Applies a cooldown to a monster's techniques, delaying their availability
    within a specified recharge range.

    **Parameters**
    - ``objectives``: The targets affected (e.g. ``own_monster``, ``enemy_monster``,
      or a combination like ``enemy_monster:own_monster``).
    - ``next_use``: The number of turns to delay before the technique can be used again.
      Must be within ``RECHARGE_RANGE``.
    - ``parameter``: The technique attribute to check (e.g. ``category``, ``range``, etc.).
    - ``value``: The expected attribute value (e.g. ``animal`` for category).

    **Example**

    .. code-block:: json

        "effects": [
            "cooldown enemy_monster 2 category animal"
        ]
    """

    name = "cooldown"
    objectives: str
    next_use: int
    parameter: str
    value: str

    def apply_tech_target(
        self, session: Session, tech: Technique, user: Monster, target: Monster
    ) -> TechEffectResult:

        if not _is_next_use_valid(self.next_use):
            raise ValueError(
                f"{self.name}: {self.next_use} must be between {RECHARGE_RANGE}"
            )

        hit = session.client.combat_session.get_tech_hit(user)
        tech.hit = tech.accuracy >= hit
        if not tech.hit:
            return TechEffectResult(name=tech.name)

        objectives = self.objectives.split(":")
        monsters = session.client.combat_session.get_target_monsters(
            objectives, user, target
        )
        moves_to_update = [
            move for mon in monsters for move in mon.moves.get_moves()
        ]

        if self.parameter == "types":
            moves_to_update = [
                move for move in moves_to_update if move.has_type(self.value)
            ]
        else:
            moves_to_update = [
                move
                for move in moves_to_update
                if not CommonCondition().check_parameter(
                    move, self.parameter, self.value
                )
            ]

        _update_moves(moves_to_update, self.next_use)
        if self.next_use > 0:
            tech.next_use -= 1

        return TechEffectResult(name=tech.name, success=True)


def _is_next_use_valid(next_use: int) -> bool:
    return RECHARGE_RANGE[0] <= next_use <= RECHARGE_RANGE[1]


def _update_moves(moves: list[Technique], next_use: int) -> None:
    for move in moves:
        if next_use == 0:
            move.next_use -= 1
        else:
            if move.next_use <= move.recharge_length:
                move.next_use = min(
                    move.next_use + next_use, RECHARGE_RANGE[1]
                )
