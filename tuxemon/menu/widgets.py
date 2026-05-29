# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""Custom pygame_menu widgets used by Tuxemon menus."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pygame
from pygame_menu.utils import make_surface
from pygame_menu.widgets import Label

if TYPE_CHECKING:
    from pygame_menu.menu import Menu


class ShadowLabel(Label):
    """A label that draws its own pixel-perfect drop shadow.

    pygame_menu's built-in font shadow is already a per-widget property
    (``font_shadow``), but it composites the shadow onto a surface sized to
    the text, so a shadow offset towards the bottom-right loses its right and
    bottom edges. This subclass enlarges the surface by the shadow offset so
    the shadow is drawn in full.

    Because the shadow is just the same glyph surface blitted at a whole-pixel
    offset, the result stays pixel-perfect. The shadow is controlled entirely
    by the inherited ``font_shadow``/``font_shadow_color``/
    ``font_shadow_offset``/``font_shadow_position`` properties.
    """

    def _render_string(
        self, string: str, color: Any
    ) -> pygame.surface.Surface:
        text = self._font_render_string(string, color)

        if not self._font_shadow:
            surface = make_surface(
                text.get_width(), text.get_height(), alpha=True
            )
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
        # A negative offset shifts the shadow up/left, so the text moves
        # down/right within the enlarged surface (and vice versa).
        surface.blit(shadow, (max(offset_x, 0), max(offset_y, 0)))
        surface.blit(text, (max(-offset_x, 0), max(-offset_y, 0)))
        return surface


def add_label(
    menu: Menu, title: str, *, shadow: bool = False, **kwargs: Any
) -> Any:
    """Add a label to ``menu``.

    When ``shadow`` is ``True`` the label is created as a :class:`ShadowLabel`
    with its font shadow enabled, giving a pixel-perfect drop shadow. The
    shadow colour, offset and position come from the menu theme (or may be
    overridden with the usual ``font_shadow_*`` keyword arguments).

    Otherwise this is equivalent to ``menu.add.label(title, **kwargs)``.
    """
    manager = menu.add
    if not shadow:
        return manager.label(title, **kwargs)

    kwargs.setdefault("font_shadow", True)
    label_id = kwargs.pop("label_id", "")
    # _filter_widget_attributes consumes the recognised keyword arguments and
    # falls back to theme defaults for anything not supplied.
    attributes = manager._filter_widget_attributes(kwargs)
    widget = ShadowLabel(title=title, label_id=label_id)
    manager._check_kwargs(kwargs)
    manager._configure_widget(widget=widget, **attributes)
    manager._append_widget(widget)
    return widget
