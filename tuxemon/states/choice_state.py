# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from pygame_menu.locals import POSITION_EAST

from tuxemon.menu.menu import PygameMenuState
from tuxemon.menu.pixel_grid import (
    ARBATA_POPUP_MARGIN,
    finish_pixel_menu,
    setup_pixel_theme,
    uses_arbata,
)
from tuxemon.menu.theme import get_theme
from tuxemon.menu.transitions import PopInClamped
from tuxemon.ui.menu_options import MenuOptions

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient


@dataclass
class MenuStateConfig:
    max_elements: int = 13
    max_height_percentage: float = 0.8


class ChoiceState(PygameMenuState):
    """
    Game state with a graphic box and some text in it.

    Pressing the action button:
    * if text is being displayed, will cause text speed to go max
    * when text is displayed completely, then will show the next message
    * if there are no more messages, then the dialog will close
    """

    name: ClassVar[str] = "ChoiceState"

    def __init__(
        self,
        client: BaseClient,
        menu: MenuOptions,
        escape_key_exits: bool = False,
        config: MenuStateConfig | None = None,
        **kwargs: Any,
    ) -> None:
        self.config = config or MenuStateConfig()
        scale = client.context.scaling.scale_int(1)
        locale = client.config.locale
        # Arbata is drawn at its pixel size, so the menu can sit on the
        # nominal pixel grid; other locales' fonts can't.
        pixel_perfect = uses_arbata(locale)

        super().__init__(
            client=client,
            transition=PopInClamped(
                max_height_percentage=self.config.max_height_percentage,
                grid=scale if pixel_perfect else None,
                margin=ARBATA_POPUP_MARGIN,
            ),
            **kwargs,
        )

        theme = get_theme(self.client.context.scaling).copy()
        if pixel_perfect:
            setup_pixel_theme(theme, locale, self.font_type, scale)

        if len(menu.options) > self.config.max_elements:
            theme.scrollarea_position = POSITION_EAST

        self._menu_config["theme"] = theme

        for option in menu.get_menu():
            self.menu.add.button(
                option.display_text,
                option.action,
                # Arbata has one (pixel) size, set by the theme.
                font_size=(
                    self.font_type.arbata
                    if pixel_perfect
                    else self.font_type.medium
                ),
            )

        if pixel_perfect:
            finish_pixel_menu(self.menu, scale, ARBATA_POPUP_MARGIN)

        self.escape_key_exits = escape_key_exits
