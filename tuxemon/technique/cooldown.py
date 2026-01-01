# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class Cooldown:
    def __init__(self, duration: int = 0):
        self.duration = duration
        self.remaining = 0

    @property
    def is_recharging(self) -> bool:
        return self.remaining > 0

    def add(self, amount: int, max_value: int) -> None:
        if amount < 0:
            logger.error("Cooldown.add() does not accept negative values")
            return
        self.remaining = min(self.remaining + amount, max_value)

    def trigger(self) -> None:
        self.remaining = self.duration

    def tick(self, amount: int = 1) -> None:
        if amount < 0:
            logger.error("Cooldown.tick() does not accept negative values")
            return
        self.remaining = max(0, self.remaining - amount)

    def reset(self) -> None:
        self.remaining = 0
