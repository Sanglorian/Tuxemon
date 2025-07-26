# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, TechEffectResult
from tuxemon.locale import T

if TYPE_CHECKING:
    from tuxemon.monster import Monster
    from tuxemon.session import Session
    from tuxemon.technique.technique import Technique


@dataclass
class PlagueEffect(CoreEffect):
    """
    Plague is an effect that can infect a monster with a specific disease,
    with a configurable spreadness.

    Attributes:
        plague_slug: The slug of the plague to apply.
        spreadness: The chance of the plague spreading to the target monster.
    """

    name = "plague"
    plague_slug: str
    spreadness: float

    def apply_tech_target(
        self, session: Session, tech: Technique, user: Monster, target: Monster
    ) -> TechEffectResult:

        if random.random() < self.spreadness and (
            target.plague.has_plague(self.plague_slug)
            or not target.plague.is_inoculated_against(self.plague_slug)
        ):
            target.plague.infect(self.plague_slug)
            success = True
        else:
            success = False

        params = {"target": target.name.upper()}
        extra = [
            T.format(
                (
                    "combat_state_plague3"
                    if target.plague.is_infected_with(self.plague_slug)
                    else "combat_state_plague0"
                ),
                params,
            )
        ]

        return TechEffectResult(name=tech.name, success=success, extras=extra)
