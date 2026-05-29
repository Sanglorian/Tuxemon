# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""Rendering patches for pygame_menu used by Tuxemon menus."""

from __future__ import annotations

from typing import Any

from pygame.surface import Surface
from pygame_menu.utils import make_surface
from pygame_menu.widgets.core.widget import Widget

_SHADOW_PATCH_APPLIED = False


def _render_string_unclipped(self: Widget, string: str, color: Any) -> Surface:
    """Render text (and its font shadow) without clipping the shadow.

    pygame_menu's stock renderer composites the shadow onto a surface the size
    of the text, so a shadow offset towards the bottom-right loses its right
    and bottom edges. This version enlarges the surface by the shadow offset so
    the shadow is drawn in full.

    The shadow is the same glyph surface blitted at a whole-pixel offset, so as
    long as the text itself is pixel-perfect the drop shadow is too.
    """
    text = self._font_render_string(string, color)

    if not self._font_shadow:
        surface = make_surface(text.get_width(), text.get_height(), alpha=True)
        surface.blit(text, (0, 0))
        return surface

    offset_x = int(self._font_shadow_tuple[0])
    offset_y = int(self._font_shadow_tuple[1])

    surface = make_surface(
        text.get_width() + abs(offset_x),
        text.get_height() + abs(offset_y),
        alpha=True,
    )
    shadow = self._font_render_string(string, self._font_shadow_color)
    # A negative offset points the shadow up/left, so the text is what shifts
    # within the enlarged surface; a positive (down-right) offset leaves the
    # text at the origin and grows the surface into the empty bottom-right.
    surface.blit(shadow, (max(offset_x, 0), max(offset_y, 0)))
    surface.blit(text, (max(-offset_x, 0), max(-offset_y, 0)))
    return surface


def install_pixel_perfect_shadow() -> None:
    """Globally replace pygame_menu's clipping font-shadow renderer.

    Idempotent. Every pygame_menu widget (labels, buttons, text inputs, ...)
    renders text through ``Widget._render_string``, so this upgrades the drop
    shadow for the whole game in one place.
    """
    global _SHADOW_PATCH_APPLIED
    if _SHADOW_PATCH_APPLIED:
        return
    Widget._render_string = _render_string_unclipped  # type: ignore[method-assign]
    _SHADOW_PATCH_APPLIED = True
