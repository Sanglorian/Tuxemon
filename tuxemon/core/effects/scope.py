# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, TechEffectResult
from tuxemon.locale.locale import T

if TYPE_CHECKING:
    from tuxemon.monster.monster import Monster
    from tuxemon.session import Session
    from tuxemon.technique.technique import Technique


@dataclass
class ScopeEffect(CoreEffect):
    """
    Applies the "scope" effect to a technique.

    This effect scans the target monster's combat statistics and displays
    them to the player. It is typically used for reconnaissance in battle,
    allowing the user to evaluate the opponent's strengths and weaknesses.

    The scan is gated on the technique's potency. The roll is cached per
    monster per round, so it shares that roll with any other potency-gated
    effect of the same technique.

    **Example**

    .. code-block:: json

        "effects": [
            "scope"
        ]
    """

    name = "scope"

    def apply_tech_target(
        self, session: Session, tech: Technique, user: Monster, target: Monster
    ) -> TechEffectResult:
        if not self.passes_potency(session, tech, user):
            return TechEffectResult(name=tech.name, success=False)

        params = {
            "AR": target.armour,
            "DE": target.dodge,
            "ME": target.melee,
            "RD": target.ranged,
            "SD": target.speed,
        }
        extra = [T.format("combat_scope", params)]
        return TechEffectResult(name=tech.name, success=True, extras=extra)
