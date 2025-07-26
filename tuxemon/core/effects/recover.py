# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, StatusEffectResult
from tuxemon.db import EffectPhase
from tuxemon.formula import simple_recover
from tuxemon.locale import T

if TYPE_CHECKING:
    from tuxemon.monster import Monster
    from tuxemon.session import Session
    from tuxemon.status.status import Status


@dataclass
class RecoverEffect(CoreEffect):
    """
    This effect has a chance to apply the recovering status effect.

    Parameters:
        divisor: The number by which user HP is to be divided.

    """

    name = "recover"
    divisor: int

    def apply_status_target(
        self, session: Session, status: Status, target: Monster
    ) -> StatusEffectResult:
        extra: list[str] = []
        healing: bool = False
        if status.has_phase(EffectPhase.PERFORM_STATUS):
            user = status.get_host()
            heal = simple_recover(user, self.divisor)
            user.current_hp = min(user.hp, user.current_hp + heal)
            healing = bool(heal)
        # check for recover (completely healed)
        if (
            status.has_phase(EffectPhase.CHECK_PARTY_HP)
            and target.current_hp >= target.hp
        ):
            target.status.clear_status(session)
            # avoid "overcome" hp bar
            if target.current_hp > target.hp:
                target.current_hp = target.hp
            params = {"target": target.name.upper()}
            extra = [T.format("combat_state_recover_failure", params)]

        return StatusEffectResult(
            name=status.name, success=healing, extras=extra
        )
