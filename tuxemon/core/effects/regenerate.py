# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, ItemEffectResult
from tuxemon.db import EffectPhase
from tuxemon.formula import simple_recover
from tuxemon.locale.locale import T

if TYPE_CHECKING:
    from tuxemon.item.item import Item
    from tuxemon.monster.monster import Monster
    from tuxemon.session import Session


@dataclass
class RegenerateEffect(CoreEffect):
    """
    Heals the holder of a held item at the end of every round.

    The amount restored is a fraction of the holder's maximum HP, so it
    scales with the monster. Nothing happens while the holder is already
    at full health.

    **Parameters**

    - ``divisor``: Integer value used to calculate the healing amount.
      The holder's maximum HP is divided by it (e.g. ``16`` restores
      1/16th of the maximum HP each round).

    **Example**

    .. code-block:: json

        "effects": [
            "regenerate 16"
        ]
    """

    name = "regenerate"
    divisor: int

    def apply_item_target(
        self, session: Session, item: Item, target: Monster
    ) -> ItemEffectResult:
        if not item.has_phase(EffectPhase.END_OF_ROUND):
            return ItemEffectResult(name=item.name)

        heal = simple_recover(target, self.divisor)
        if heal <= 0:
            return ItemEffectResult(name=item.name)

        target.current_hp += heal
        params = {"target": target.name, "name": item.name}
        return ItemEffectResult(
            name=item.name,
            success=True,
            extras=[T.format("combat_state_regenerate", params)],
        )
