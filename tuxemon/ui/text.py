# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional, Union

from pygame import SRCALPHA
from pygame.font import Font
from pygame.rect import Rect
from pygame.surface import Surface

from tuxemon import prepare
from tuxemon.graphics import ColorLike
from tuxemon.sprite import Sprite
from tuxemon.ui.draw import (
    MultilineTextRenderer,
    TextRenderer,
    iter_render_text,
)

min_font_size = 7


class VerticalAlignment(Enum):
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"


class HorizontalAlignment(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class TextArea(Sprite):
    """Area of the screen that can draw text."""

    animated = True

    def __init__(
        self,
        font: Font,
        font_color: ColorLike,
        font_shadow: ColorLike = prepare.FONT_SHADOW_COLOR,
        background_color: Optional[ColorLike] = None,
        background_image: Optional[Surface] = None,
        alignment: str = "left",
        vertical_alignment: str = "top",
    ) -> None:
        super().__init__()
        self.rect = Rect(0, 0, 0, 0)
        self.drawing_text = False
        self.font = font
        self.font_color = font_color
        self.font_shadow = font_shadow
        self._text_renderer = TextRenderer(
            font=self.font,
            font_color=self.font_color,
            font_shadow_color=self.font_shadow,
        )
        self.background_color = background_color
        self.background_image = background_image
        self.alignment = alignment
        self.vertical_alignment = vertical_alignment
        self._rendered_text = None
        self._text_rect = None
        self._text = ""

    def __iter__(self) -> TextArea:
        return self

    def __len__(self) -> int:
        return len(self._text)

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        if value != self._text:
            self._text = value

        if self.animated:
            self._start_text_animation()
        else:
            self.image = self._text_renderer.shadow_text(self._text)

    def __next__(self) -> None:
        if self.animated:
            try:
                dest, scrap = next(self._iter)
                self.image.blit(scrap, dest)
            except StopIteration:
                self.drawing_text = False
                raise
        else:
            raise StopIteration

    next = __next__

    def set_background(
        self,
        background_color: Optional[ColorLike] = None,
        background_image: Optional[Surface] = None,
    ) -> None:
        self.image = Surface(self.rect.size, SRCALPHA)

        if background_color:
            self.image.fill(background_color)
        if background_image:
            self.image.blit(background_image, (0, 0))

    def _start_text_animation(self) -> None:
        self.drawing_text = True
        self.image = Surface(self.rect.size, SRCALPHA)

        if self.background_color:
            self.image.fill(self.background_color)
        if self.background_image:
            self.image.blit(self.background_image, (0, 0))

        self._iter = iter_render_text(
            text=self._text,
            font=self.font,
            fg=self.font_color,
            bg=self.font_shadow,
            rect=self.image.get_rect(),
            alignment=self.alignment,
            vertical_alignment=self.vertical_alignment,
        )


def draw_text(
    surface: Surface,
    text: str,
    rect: Union[Rect, tuple[int, int, int, int]],
    *,
    justify: Literal["left", "center", "right"] = "left",
    align: Literal["top", "middle", "bottom"] = "top",
    font: Font,
    font_size: Optional[int] = None,
    font_color: Optional[ColorLike] = None,
    text_renderer: Optional[TextRenderer] = None,
) -> None:
    """
    Draws text to a surface.

    If the text exceeds the rect size, it will autowrap. To place text on a
    new line, put TWO newline characters (\\n)  in your text.

    Parameters:
        text: The text that you want to draw to the current menu item.
        rect: Area where the text will be placed.
        justify: Left, center, or right justify the text.
        align: Align the text to the top, middle, or bottom of the menu.
        font: Font to use to draw the text.
        font_size: Size of the font in pixels BEFORE scaling is done. *Default: 4*
        font_color: Tuple of RGB values of the font _color to use.

    .. image:: images/menu/justify_center.png
    """
    left, top, width, height = rect

    if width <= 0 or height <= 0:
        return

    _left: float = left
    _top: float = top

    if not font_color:
        font_color = prepare.FONT_COLOR

    if text_renderer is None:
        text_renderer = TextRenderer(font_color=font_color, font=font)

    if not text:
        return

    ml_renderer = MultilineTextRenderer(text_renderer)
    line_surfaces = ml_renderer.render_lines(text, width)

    total_text_height = sum(height for _, height in line_surfaces)

    if align == "middle":
        _top = top + (height - total_text_height) / 2
    elif align == "bottom":
        _top = top + height - total_text_height

    if justify == "center":
        _left = (
            left
            + (
                width
                - max(surface.get_width() for surface, _ in line_surfaces)
            )
            / 2
        )
    elif justify == "right":
        _left = (
            left
            + width
            - max(surface.get_width() for surface, _ in line_surfaces)
        )

    for text_surface, line_height in line_surfaces:
        surface.blit(text_surface, (_left, _top))
        _top += line_height + ml_renderer.line_spacing
