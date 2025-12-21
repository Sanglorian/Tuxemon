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
    from tuxemon.session import Session
    from tuxemon.status.status import Status

logger = logging.getLogger(__name__)


@dataclass
class StatChangeEffect(CoreEffect):
    """
    Applies the "statchange" status effect.

    This effect modifies one or more combat-relevant stats of a monster
    during battle. Changes can be applied either through direct value-based
    operations (e.g., add, subtract, divide) or through step-based scaling
    relative to the stat's base value. Step-based scaling supports clamping
    via ``max_step_limit`` to maintain balance.

    **Supported Stats**
    - ``speed``
    - ``armour``
    - ``melee``
    - ``ranged``
    - ``dodge``
    - ``hp`` → modifies permanent base HP
    - ``current_hp`` → modifies runtime health

    **Parameters (per stat modifier)**
    - ``value``: Float, direct adjustment applied to the stat (ignored if ``step`` is used).
    - ``step``: Integer, step delta for scaling (e.g., +2 steps to speed).
    - ``max_deviation``: Optional integer, adds randomness to ``step`` or ``value``.
    - ``max_step_limit``: Float, maximum cumulative scaling boundary (e.g., ±0.5 for ±50%).
    - ``scaling_mode``: String, either ``linear`` (base * (1 + step)) or ``nonlinear`` (tiered multipliers).
    - ``operation``: String, arithmetic operation for value logic (``add``, ``subtract``, ``divide``).
    - ``overridetofull``: Boolean, if ``True`` and stat is HP, restores current HP to maximum.

    **Example**

    .. code-block:: json

        "effects": [
            "statchange"
        ]

        "stat_modifiers": {
            "speed": {
                "step": 2,
                "max_deviation": 1,
                "max_step_limit": 0.5,
                "scaling_mode": "linear"
            },
            "current_hp": {
                "overridetofull": true
            }
        }
    """

    name = "statchange"

    def apply_status(
        self, session: Session, status: Status
    ) -> StatusEffectResult:
        host = status.host
        if (
            status.has_phase(EffectPhase.PERFORM_STATUS)
            and self.name not in status._effect_applied
        ):
            status._effect_applied.add("statchange")

            for stat_slug, stat_model in status.stat_modifiers.items():
                if not stat_model:
                    continue

                step_delta = stat_model.step
                raw_value = stat_model.value
                max_dev = stat_model.max_deviation
                override = stat_model.overridetofull
                operation = stat_model.operation

                # Handle HP override
                if stat_slug == "current_hp" and override:
                    host.current_hp = host.hp
                    logger.info(
                        f"[{status.name}] Overriding current HP > {host.name}: {host.hp}"
                    )
                    continue

                new_value = 0

                if step_delta is not None:
                    scaling_mode = stat_model.scaling_mode
                    max_step = stat_model.max_step_limit

                    actual_step = (
                        random.randint(
                            step_delta - max_dev, step_delta + max_dev
                        )
                        if max_dev
                        else step_delta
                    )

                    # Clamp actual step to allowable range
                    actual_step = int(
                        max(-max_step, min(max_step, actual_step))
                    )

                    if stat_slug == "current_hp":
                        base = host.hp
                    else:
                        base = getattr(host.base_stats, stat_slug)

                    current = host.return_stat(StatType(stat_slug))
                    old_step = (current - base) / base
                    total_step = max(
                        -max_step,
                        min(max_step, old_step + actual_step),
                    )

                    if scaling_mode == "linear":
                        new_value = int(base * (1 + total_step))
                    else:
                        # Nonlinear tiered formula
                        if total_step > 0:
                            new_value = int(
                                base * (max_step + total_step) / max_step
                            )
                        else:
                            new_value = int(
                                base * max_step / (max_step - total_step)
                            )

                    logger.debug(
                        f"[{status.name}] {stat_slug} changed via {scaling_mode} step on {host.name}: "
                        f"step {old_step:.3f} > {total_step:.3f}, value {current:.2f} > {new_value:.2f}"
                    )

                else:
                    # Value-based logic
                    applied_value = (
                        random.randint(
                            int(raw_value - max_dev), int(raw_value + max_dev)
                        )
                        if max_dev
                        else raw_value
                    )

                    stat_base = (
                        getattr(host, stat_slug)
                        if stat_slug == "current_hp"
                        else getattr(host.base_stats, stat_slug, None)
                    )
                    if stat_base is None:
                        continue

                    if operation not in ops_dict:
                        logger.warning(
                            f"Unknown operation '{operation}' in status '{status.name}'"
                        )
                        continue

                    op_func = ops_dict.get(operation, lambda a, b: a)
                    new_value = round(op_func(stat_base, applied_value))

                    logger.debug(
                        f"[{status.name}] {stat_slug} changed via value on {host.name}: "
                        f"{stat_base} > {new_value}"
                    )

                # Safety: Clamp stat values
                if new_value <= 0 and stat_slug != "current_hp":
                    new_value = 1

                # Assignment
                if stat_slug == "current_hp":
                    host.current_hp = min(new_value, host.hp)
                elif stat_slug in StatType.__members__:
                    setattr(host.base_stats, stat_slug, int(new_value))

        elif status.has_phase(EffectPhase.ON_END):
            host.set_stats()

        return StatusEffectResult(name=status.name, success=True)
