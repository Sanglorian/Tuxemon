# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, TechEffectResult
from tuxemon.db import BlockedReason
from tuxemon.locale.locale import T
from tuxemon.status.status import Status

if TYPE_CHECKING:
    from tuxemon.monster.monster import Monster
    from tuxemon.session import Session
    from tuxemon.technique.technique import Technique


@dataclass
class TransferEffect(CoreEffect):
    """
    Applies the "transfer" effect to a technique.

    This effect moves a specified condition (status) from one entity to
    another. The direction of transfer is controlled by the ``direction``
    attribute, which determines whether the condition is passed from the
    user to the target or vice versa.

    The condition is applied to the destination through the normal status
    lifecycle (``MonsterStatusHandler.apply_status``): the destination's
    previous status ends properly (``ON_END``), the incoming one starts
    (``ON_START``), and immunity and transition rules apply.

    The condition always leaves the source, whether or not it takes hold
    on the destination, and the effect still counts as a success. This is
    intended: transferring a condition onto a monster that is immune to it
    (or whose current status blocks it) destroys the condition outright,
    and the user is still cured. The reason the condition did not take
    hold is reported in the result's ``extras``.

    **Parameters**

    - ``condition``: String name of the condition to transfer.
    - ``direction``: String specifying the transfer direction.
      - ``user_to_target`` → transfers condition from the user to the target.
      - ``target_to_user`` → transfers condition from the target to the user.

    **Example**

    .. code-block:: json

        "effects": [
            "transfer poison user_to_target"
        ]

        "effects": [
            "transfer burn target_to_user"
        ]
    """

    name = "transfer"
    condition: str
    direction: str

    def apply_tech_target(
        self, session: Session, tech: Technique, user: Monster, target: Monster
    ) -> TechEffectResult:
        hit = session.client.combat_session.get_tech_hit(user)
        tech.hit = tech.accuracy >= hit
        done = False
        extras: list[str] = []
        if tech.hit:
            source, dest = (
                (user, target)
                if self.direction == "user_to_target"
                else (target, user)
            )
            if source.status.has_status(self.condition):
                source.status.clear_status(session)
                new_status = Status.create(self.condition, dest, dest.steps)
                result = dest.status.apply_status(session, new_status)
                done = True
                if result.blocked_reason == BlockedReason.IMMUNE_BY_ITEM:
                    params = {
                        "target": f"{dest.name} ({result.blocked_by})",
                        "method": new_status.name,
                    }
                    extras.append(T.format("combat_state_immune", params))
                elif result.blocked_reason == BlockedReason.ALREADY_PRESENT:
                    # the destination already had this condition, which was
                    # simply refreshed: nothing was rejected
                    pass
                elif not result.applied and result.blocked_by:
                    params = {
                        "method": result.blocked_by,
                        "target": dest.name,
                        "condition": new_status.name,
                    }
                    extras.append(T.format("combat_state_prevented", params))
        return TechEffectResult(name=tech.name, success=done, extras=extras)
