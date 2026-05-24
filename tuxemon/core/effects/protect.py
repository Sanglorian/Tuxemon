# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, TechEffectResult

if TYPE_CHECKING:
    from tuxemon.monster.monster import Monster
    from tuxemon.session import Session
    from tuxemon.technique.technique import Technique


@dataclass
class ProtectEffect(CoreEffect):
    """
    Blocks incoming techniques that match a specified criterion for the
    current turn.

    When the protected monster is targeted by a damaging technique whose
    ``field`` attribute equals ``value``, the damage is negated. Protection
    expires automatically at the end of the turn — no cleanup technique is
    required.

    **Parameters**

    - ``field``: The technique attribute to match. Valid values:

      - ``category`` — matches ``TechCategory`` (e.g. ``special``, ``animal``)
      - ``type`` — matches an element type slug (e.g. ``fire``, ``water``)
      - ``range`` — matches ``Range`` (e.g. ``melee``, ``ranged``, ``touch``)
      - ``sort`` — matches ``TechSort`` (``damage`` or ``meta``)

    - ``value``: The specific value of ``field`` to block.

    **Example**

    .. code-block:: json

        "effects": [
            "protect category special"
        ]

    Multiple protect effects on the same technique stack, blocking all
    matched criteria simultaneously:

    .. code-block:: json

        "effects": [
            "protect type fire",
            "protect range melee"
        ]
    """

    name = "protect"
    field: str
    value: str

    def apply_tech_target(
        self, session: Session, tech: Technique, user: Monster, target: Monster
    ) -> TechEffectResult:
        turn = session.client.combat_session.turn
        user.protect_blocklist.append((self.field, self.value, turn))
        return TechEffectResult(name=tech.name, success=True)
