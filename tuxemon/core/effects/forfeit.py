# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, TechEffectResult
from tuxemon.locale.locale import T

if TYPE_CHECKING:
    from tuxemon.entity.npc import NPC
    from tuxemon.monster.monster import Monster
    from tuxemon.session import Session
    from tuxemon.technique.technique import Technique


@dataclass
class ForfeitEffect(CoreEffect):
    """
    Applies the "forfeit" effect in combat.

    This effect represents surrendering a battle. It faints the entire party
    of the forfeiting player and then lets the normal combat resolution take
    over. Because the forfeiting player has no monsters left, the regular
    state machine treats them as defeated and the battle is handled in every
    way like an ordinary loss: the outcome is recorded as ``lost``, the loss
    is written to the battle history, and the standard defeat music and
    messaging are shown.

    **Example**

    .. code-block:: json

        "effects": [
            "forfeit"
        ]
    """

    name = "forfeit"

    def apply_tech_target(
        self, session: Session, tech: Technique, user: Monster, target: Monster
    ) -> TechEffectResult:
        player = user.get_owner()

        params = {"npc": session.client.combat_session.right_player.name.upper()}
        extras = [T.format("combat_forfeit", params)]

        # Faint the whole party. The combat state machine will detect the
        # defeated player on the next resolution and run the same loss flow
        # (track_battles -> HAS_WINNER) as a regular defeat.
        self._faint_all_monsters(player)

        return TechEffectResult(name=tech.name, success=True, extras=extras)

    def _faint_all_monsters(self, char: NPC) -> None:
        for monster in char.monsters:
            monster.current_hp = 0
