# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, final

from tuxemon.event.eventaction import EventAction
from tuxemon.session import Session

logger = logging.getLogger(__name__)


@final
@dataclass
class BoundarySetAction(EventAction):
    """
    Replaces the current boundary with a new one, or resets to default
    if no parameters are given.

    Script usage:
        .. code-block::

            boundary_set [shape][,values]

    Script parameters:
        shape: Optional. Either "rectangle" or "circle".
        values: Optional. A colon-separated string of integers:
            - For "rectangle": x0:x1:y0:y1
            - For "circle": cx:cy:radius
    """

    name = "boundary_set"
    shape: Optional[str] = None
    values: Optional[str] = None

    def start(self, session: Session) -> None:
        checker = session.client.boundary

        if not self.shape and not self.values:
            checker.reset_to_default()
            logger.debug("Boundary reset to default.")
            return

        if not self.shape or not self.values:
            logger.warning(
                "BoundarySetAction requires both shape and values, or neither."
            )
            return

        parts = self.values.split(":")
        try:
            nums = [int(p) for p in parts]
        except ValueError:
            logger.warning(
                f"Invalid numeric values in boundary_set: {self.values}"
            )
            return

        if self.shape == "rectangle" and len(nums) == 4:
            x0, x1, y0, y1 = nums
            checker.set_rectangular_boundary("event", x0, x1, y0, y1)

        elif self.shape == "circle" and len(nums) == 3:
            cx, cy, radius = nums
            checker.set_circular_boundary("event", (cx, cy), radius)

        else:
            logger.warning(
                f"Invalid shape or parameter count: {self.shape}, {self.values}"
            )
