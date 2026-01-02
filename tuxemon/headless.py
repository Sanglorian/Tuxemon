# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""Headless initialization for Tuxemon (no pygame dependency)."""
from __future__ import annotations

import logging
from typing import Any

from tuxemon.user_config import CONFIG

logger = logging.getLogger(__name__)


class DummySurface:
    def __init__(self, size: tuple[int, int]):
        self.size = size

    def get_size(self) -> tuple[int, int]:
        return self.size

    def copy(self) -> DummySurface:
        return DummySurface(self.size)


class DummyRect:
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    @property
    def right(self) -> int:
        return self.x + self.w

    def copy(self) -> DummyRect:
        return DummyRect(self.x, self.y, self.w, self.h)


SCREEN: DummySurface | None = None
SCREEN_RECT: DummyRect | None = None
JOYSTICKS: list[Any] = []


def headless_init() -> None:
    """Initializes game components for a headless environment."""
    from tuxemon.db import db
    from tuxemon.locale import T

    T.initialize_translations(recompile=CONFIG.recompile_translations)
    db.load()
    logger.debug("headless init")

    global SCREEN, SCREEN_RECT, JOYSTICKS
    SCREEN = DummySurface(CONFIG.resolution)
    SCREEN_RECT = DummyRect(0, 0, *CONFIG.resolution)
    JOYSTICKS = []
