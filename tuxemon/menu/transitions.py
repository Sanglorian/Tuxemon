# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import math
from typing import Protocol

from pygame_menu import Menu
from pygame_menu.locals import SCROLLAREA_POSITION_NONE

from tuxemon.menu.pixel_grid import (
    NO_MARGIN,
    Margin,
    grid_menu_size,
)
from tuxemon.prepare import DisplayContext


class MenuTransition(Protocol):
    def apply(
        self, menu: Menu, progress: float, context: DisplayContext
    ) -> None: ...


class PopInClamped:
    """Zoom-in animation that scales the menu while clamping size to screen bounds.

    With ``grid`` (the display scale), the menu opens to fit its entries
    plus ``margin``, in whole nominal pixels, at a position on the nominal
    pixel grid. Use it with ``keep_on_grid`` (and the same margin) to put
    the entries on the grid too.
    """

    def __init__(
        self,
        max_height_percentage: float = 0.8,
        grid: int | None = None,
        margin: Margin = NO_MARGIN,
    ) -> None:
        self._base_size: tuple[int, int] | None = None
        self.max_height_percentage = max_height_percentage
        self.grid = grid
        self.margin = margin

    def apply(
        self, menu: Menu, progress: float, context: DisplayContext
    ) -> None:

        if self._base_size is None:
            if self.grid:
                width, height = grid_menu_size(menu, self.grid, self.margin)
            else:
                width, height = menu.get_size(widget=True)
            self._base_size = (int(width), int(height))

        assert self._base_size is not None
        base_w, base_h = self._base_size

        screen_w, screen_h = context.resolution

        # Clamp base size to screen bounds
        max_h = int(screen_h * self.max_height_percentage)
        if self.grid:
            max_h = max_h // self.grid * self.grid
        if self.grid and base_h > max_h:
            # It will scroll: make room for the scrollbar, if it has one.
            theme = menu.get_theme()
            if theme.scrollarea_position != SCROLLAREA_POSITION_NONE:
                base_w += theme.scrollbar_thick
        base_w = min(base_w, screen_w)
        base_h = min(base_h, max_h)

        # Avoid zero scale
        scale = max(0.01, progress)

        w = max(1, int(base_w * scale))
        h = max(1, int(base_h * scale))

        if not self.grid:
            menu.resize(w, h)
            return

        # Centre on the grid. The frame is drawn around this, and its
        # width is a whole number of nominal px too.
        grid = self.grid
        x = (screen_w - w) // 2 // grid * grid
        y = (screen_h - h) // 2 // grid * grid
        menu.resize(w, h, position=(x, y, False))


class SlideRight:
    """Slide the menu in from the right edge of the screen."""

    def __init__(self) -> None:
        self._width: int | None = None

    def apply(
        self, menu: Menu, progress: float, context: DisplayContext
    ) -> None:

        if self._width is None:
            self._width = menu.get_width(border=True)

        # Original behavior:
        # animation_offset = width * progress
        # menu.translate(-animation_offset, 0)
        offset = -int(self._width * progress)

        menu.translate(offset, 0)


class EaseOut:
    """Easing curve that accelerates quickly and slows toward the end."""

    def __call__(self, t: float) -> float:
        return math.sin(t * math.pi / 2)
