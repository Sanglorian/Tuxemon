# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, StatusEffectResult
from tuxemon.db import EffectPhase

if TYPE_CHECKING:
    from tuxemon.session import Session
    from tuxemon.status.status import Status


@dataclass
class WastingEffect(CoreEffect):
    """
    Applies the "wasting" status effect.

    This effect causes a monster to lose a fraction of its maximum HP each
    turn, with the damage increasing over time. The amount of damage scales
    based on the number of times the status has been applied.

    The ramp counts applications rather than turns: the status' turn counter
    is one-based and only runs for a status with a duration, neither of
    which suits a ramp that has to open at a single dose and last as long as
    the battle does.

    **Parameters**

      - ``divisor``: Integer divisor used to calculate base damage.
      - Example: With ``divisor = 16``, the monster takes ``max_hp / 16``
        damage the first turn, ``(max_hp / 16) * 2`` the second, and so on.

    **Example**

    .. code-block:: json

        "effects": [
            "wasting 16"
        ]
    """

    name = "wasting"
    divisor: int

    def apply_status(
        self, session: Session, status: Status
    ) -> StatusEffectResult:
        done: bool = False
        host = status.host
        if (
            status.has_phase(EffectPhase.PERFORM_STATUS)
            and not host.is_fainted
        ):
            status.advance_round()
            damage = (host.hp // self.divisor) * status.nr_use
            host.current_hp = max(0, host.current_hp - damage)
            done = True
        return StatusEffectResult(name=status.name, success=done)
