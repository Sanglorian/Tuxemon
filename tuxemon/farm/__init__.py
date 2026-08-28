# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Farming subsystem: a persistent per-tile soil/crop grid, the crops that grow on
it, and the render layer that draws them.

The farm keeps its own day counter (:class:`FarmCalendar`) rather than reading
the session's :class:`~tuxemon.time_handler.TimeHandler`. The time handler
reflects the real-world clock and is deliberately left untouched; farm days
only advance when the game explicitly asks them to.
"""

from __future__ import annotations

from tuxemon.farm.calendar import FarmCalendar
from tuxemon.farm.crop import CropModel, CropStage, PlantedCrop, load_crops
from tuxemon.farm.grid import FarmGrid, FarmTile
from tuxemon.farm.manager import FarmManager

__all__ = [
    "CropModel",
    "CropStage",
    "FarmCalendar",
    "FarmGrid",
    "FarmManager",
    "FarmTile",
    "PlantedCrop",
    "load_crops",
]
