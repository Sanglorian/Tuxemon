# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, StatusEffectResult
from tuxemon.db import EffectPhase, StatType
from tuxemon.tools import ops_dict

if TYPE_CHECKING:
    from tuxemon.monster import Monster
    from tuxemon.session import Session
    from tuxemon.status.status import Status

logger = logging.getLogger(__name__)


@dataclass
class StatChangeEffect(CoreEffect):
    """
    Applies a stat-altering effect to a target monster during combat.

    This effect modifies one or more combat-relevant stats on a monster, either
    through addition, subtraction, or division, depending on configuration. The affected
    stats are pulled from the status's stat components (e.g. `status.statmelee`, etc.),
    and can impact either permanent base stats or temporary health values.

    This class supports optional randomness via `max_deviation`, and HP overrides using
    `overridetofull` which resets current HP to the max HP.

    Effect Trigger:
        - Only applies if the status has phase `PERFORM_STATUS`.

    JSON SYNTAX (per stat object inside Status):
        {
            "value": int,               # Amount to apply to the stat (positive or negative)
            "max_deviation": int,       # Optional random deviation applied to value
            "operation": str,           # Operation: "add", "subtract", "divide" (from ops_dict)
            "overridetofull": bool      # Special case for HP: resets current HP to max HP if True
        }

    Stats Supported:
        - speed
        - armour
        - melee
        - ranged
        - dodge
        - hp         > modifies base_stats.hp
        - current_hp > modifies runtime health

    Attributes:
        name: Effect name, used for identification and serialization.

    Returns:
        StatusEffectResult: Indicates if the stat change was successful and references the status name.
    """

    name = "statchange"

    def apply_status_target(
        self, session: Session, status: Status, target: Monster
    ) -> StatusEffectResult:
        statsmaster = [
            status.statspeed,
            status.stathp,
            status.statarmour,
            status.statmelee,
            status.statranged,
            status.statdodge,
        ]
        statslugs = [
            "speed",
            "current_hp",  # special case
            "armour",
            "melee",
            "ranged",
            "dodge",
        ]
        newstatvalue = 0

        if status.has_phase(EffectPhase.PERFORM_STATUS):
            for stat, slug in zip(statsmaster, statslugs):
                if not stat:
                    continue

                value = stat.value
                max_dev = stat.max_deviation
                override = stat.overridetofull
                operation = stat.operation

                # Apply deviation properly for positive or negative values
                if max_dev:
                    min_val = value - max_dev
                    max_val = value + max_dev
                    value = random.randint(int(min_val), int(max_val))

                # Handle HP override explicitly
                if slug == "current_hp" and override:
                    target.current_hp = target.hp
                    logger.info(
                        f"[{status.name}] Overriding current HP > {target.name}: {target.hp}"
                    )
                    continue

                base_value = (
                    getattr(target, slug)
                    if slug == "current_hp"
                    else getattr(target.base_stats, slug, None)
                )
                if base_value is None:
                    continue

                newstatvalue = ops_dict[operation](base_value, value)

                if newstatvalue <= 0:
                    newstatvalue = 1  # avoid death via stat drop

                # Assign value
                if slug == "current_hp":
                    setattr(target, slug, newstatvalue)
                elif slug in StatType.__members__:
                    setattr(target.base_stats, slug, newstatvalue)

                logger.debug(
                    f"[{status.name}] {slug} changed on {target.name}: {base_value} > {newstatvalue}"
                )

        return StatusEffectResult(name=status.name, success=bool(newstatvalue))
