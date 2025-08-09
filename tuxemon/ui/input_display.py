# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pygame.font import Font
from pygame.rect import Rect

from tuxemon import tools
from tuxemon.graphics import ColorLike
from tuxemon.sprite import Sprite, SpriteGroup
from tuxemon.ui.text import TextArea


@dataclass
class InputDisplayConfig:
    prompt_offset_x: int = 50
    prompt_offset_y: int = 20
    prompt_width: int = 80
    prompt_height: int = 100
    text_area_offset_x: int = 90
    text_area_offset_y: int = 30
    text_area_width: int = 80
    text_area_height: int = 100
    char_counter_offset_x: int = 80
    char_counter_offset_y: int = 30


class InputDisplay:
    """
    Manages the display of the input prompt, the current input string,
    and the character counter.
    """

    def __init__(
        self,
        font: Font,
        font_color: ColorLike,
        prompt_text: str,
        initial_input_string: str,
        area_rect: Rect,
        config: Optional[InputDisplayConfig] = None,
    ) -> None:
        self.sprites: SpriteGroup[Sprite] = SpriteGroup()
        self.config = config or InputDisplayConfig()
        self.area_rect = area_rect

        # Prompt area
        self.prompt = TextArea(font, font_color, (96, 96, 96))
        self.prompt.animated = False
        self.prompt.rect = Rect(
            area_rect.x + tools.scale(self.config.prompt_offset_x),
            area_rect.y + tools.scale(self.config.prompt_offset_y),
            tools.scale(self.config.prompt_width),
            tools.scale(self.config.prompt_height),
        )
        self.prompt.text = prompt_text
        self.sprites.add(self.prompt)

        # Input text area
        self.text_area = TextArea(font, font_color, (96, 96, 96))
        self.text_area.animated = False
        self.text_area.rect = Rect(
            area_rect.x + tools.scale(self.config.text_area_offset_x),
            area_rect.y + tools.scale(self.config.text_area_offset_y),
            tools.scale(self.config.text_area_width),
            tools.scale(self.config.text_area_height),
        )
        self.text_area.text = initial_input_string
        self.sprites.add(self.text_area)

        # Character counter
        self.char_counter = TextArea(font, font_color, (96, 96, 96))
        self.char_counter.animated = False
        self.sprites.add(self.char_counter)

    def update_input_string(self, new_string: str) -> None:
        """Updates the displayed input string."""
        self.text_area.text = new_string

    def update_char_counter(self, remaining_chars: int) -> None:
        """Updates the character count display in a fixed position."""
        self.char_counter.text = f"{remaining_chars}"
        self.char_counter.rect.topleft = (
            self.area_rect.right
            - tools.scale(self.config.char_counter_offset_x),
            self.area_rect.top
            + tools.scale(self.config.char_counter_offset_y),
        )
