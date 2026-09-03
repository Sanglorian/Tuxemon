# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Real-time planting.

Tiles are marked "tilled" by a map event, a Fruit item is planted in one, and
the resulting Plant grows on the wall clock: every question about a Plant
(which sprite is showing, how wet it has been, what it yields) is answered by
comparing stored absolute timestamps against ``time.time()``. Nothing ticks,
so growth continues while the game is shut.
"""

from __future__ import annotations

from tuxemon.farming.config import PlantingConfig, get_planting_config
from tuxemon.farming.manager import FarmingManager
from tuxemon.farming.plot import (
    WET_DURATION,
    Plant,
    TilledTile,
    harvest_amount,
    merge_intervals,
    stage_index,
    wet_seconds,
    yield_value,
)

__all__ = [
    "FarmingManager",
    "Plant",
    "PlantingConfig",
    "TilledTile",
    "WET_DURATION",
    "get_planting_config",
    "harvest_amount",
    "merge_intervals",
    "stage_index",
    "wet_seconds",
    "yield_value",
]
