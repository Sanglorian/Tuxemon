# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon import formula
from tuxemon.core.core_effect import CoreEffect, TechEffectResult
from tuxemon.db import EffectPhase
from tuxemon.locale.locale import T

if TYPE_CHECKING:
    from tuxemon.monster.monster import Monster
    from tuxemon.session import Session
    from tuxemon.technique.technique import Technique


@dataclass
class MultiAttackEffect(CoreEffect):
    """
    Applies the "multiattack" effect to a technique.

    The technique lands up to ``times`` hits in a single turn. Accuracy is
    re-rolled before every hit and the chain stops at the first miss, so a
    low accuracy technique rarely reaches its full hit count. The chain also
    stops once the target is out of hit points: the last hit is clamped to
    the target's remaining HP so a multi-hit technique never overkills.

    Damage is applied to the target as each hit lands, exactly like the
    ``damage`` effect does. The per-hit amounts are reported back through
    ``hit_damages`` so the combat state can stage one animation cycle per
    hit.

    **Parameters**

    - ``times``: Integer value indicating how many times the technique
      can be repeated in a single turn.

    **Example**

    .. code-block:: json

        "effects": [
            "multiattack 3"
        ]
    """

    name = "multiattack"
    times: int

    def apply_tech_target(
        self, session: Session, tech: Technique, user: Monster, target: Monster
    ) -> TechEffectResult:
        combat = session.client.combat_session
        # multiattack re-rolls the hit chance for every hit, which would
        # leave the user's stored roll pointing at the last re-roll. Other
        # effects on the same technique must still be judged against the
        # technique's original roll, so it's put back afterwards.
        original_tech_hit = combat.get_tech_hit(user)

        hit_damages: list[int] = []
        extras: list[str] = []

        try:
            for _ in range(self.times):
                combat.set_tech_hit(user)
                if tech.accuracy < combat.get_tech_hit(user):
                    break

                damage, _ = formula.simple_damage_calculate(tech, user, target)
                damage = min(damage, target.current_hp)
                hit_damages.append(damage)
                target.current_hp = max(0, target.current_hp - damage)

                if target.is_fainted:
                    # a status such as diehard may bring the target back
                    extras.extend(self._react_to_fainting(session, target))
                    if target.is_fainted:
                        break
        finally:
            combat.set_tech_hit(user, original_tech_hit)

        hit_count = len(hit_damages)
        success = hit_count > 0

        if success:
            params = {"hit_count": hit_count}
            extras.insert(0, T.format("combat_multiattack", params))

        return TechEffectResult(
            name=tech.name,
            success=success,
            should_tackle=success,
            damage=sum(hit_damages),
            extras=extras,
            hit_count=hit_count,
            hit_damages=hit_damages,
        )

    @staticmethod
    def _react_to_fainting(session: Session, target: Monster) -> list[str]:
        """
        Lets the target's current status react to it running out of HP.

        Returns:
            The messages produced by the status, if any.
        """
        status = target.status.current_status
        if status is None:
            return []
        result = status.use(session, EffectPhase.CHECK_PARTY_HP)
        return list(result.extras)
