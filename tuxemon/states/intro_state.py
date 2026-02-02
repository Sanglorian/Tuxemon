# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from pygame.surface import Surface

from tuxemon.locale.locale import T
from tuxemon.menu.menu import PopUpMenu
from tuxemon.platform.const.graphics import BLACK_COLOR
from tuxemon.tools import transform_resource_filename

if TYPE_CHECKING:
    from tuxemon.platform.events import PlayerInput

logger = logging.getLogger(__name__)
MenuGameObj = Callable[[], None]


class IntroState(PopUpMenu[MenuGameObj]):
    """The state responsible for the splash screen."""

    name: ClassVar[str] = "IntroState"

    _cached_sprites = None

    def __init__(self) -> None:
        super().__init__()

        self.triggered = False

        if IntroState._cached_sprites is None:
            IntroState._cached_sprites = self._load_sprite_files()

        if IntroState._cached_sprites:
            self.load_animated_sprite(IntroState._cached_sprites, 0.07)

    def _load_sprite_files(self) -> list[str] | None:
        folder_path = Path(transform_resource_filename("animations/intro"))

        if not folder_path.is_dir():
            logger.warning("Intro folder not found. Skipping intro.")
            self.client.replace_state("StartState")
            return None

        sprite_files = sorted(
            str(p) for p in folder_path.glob("intro_*.png") if p.is_file()
        )

        if not sprite_files:
            logger.warning("Intro folder is empty. Skipping intro.")
            self.client.replace_state("StartState")
            return None

        self.client.current_music.play("music_main_theme")
        return sprite_files

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        if event.pressed and not self.triggered:
            self.client.replace_state("StartState")
        return None

    def draw(self, surface: Surface) -> None:
        if not self.triggered:
            surface.fill(BLACK_COLOR)
            self.sprites.draw(surface)
            label = self.shadow_text(T.translate("menu_intro"))
            label_rect = label.get_rect(midbottom=surface.get_rect().center)
            surface.blit(label, label_rect)
