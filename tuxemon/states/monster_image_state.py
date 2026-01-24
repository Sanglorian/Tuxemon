# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from typing import ClassVar

from pygame.surface import Surface
from pygame_menu.locals import ALIGN_CENTER

from tuxemon.menu.menu import PygameMenuState
from tuxemon.platform.events import PlayerInput
from tuxemon.prepare import SCREEN_SIZE


class MonsterImageState(PygameMenuState):
    name: ClassVar[str] = "MonsterImageState"

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        return None

    def __init__(self, background: str, surface: Surface) -> None:
        image_path = f"gfx/ui/background/{background}.png"
        self._setup_theme(image_path)
        width, height = SCREEN_SIZE
        surface = surface.copy()
        image = self._create_image_from_surface(surface)
        super().__init__(height=height, width=width)
        self.menu.add.image(image, align=ALIGN_CENTER)
        self.reset_theme()
