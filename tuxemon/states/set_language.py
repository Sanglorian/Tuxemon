# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar

from pygame_menu.locals import ALIGN_CENTER, POSITION_EAST
from pygame_menu.menu import Menu

from tuxemon.locale.locale import T
from tuxemon.menu.menu import PygameMenuState
from tuxemon.menu.pixel_grid import (
    ARBATA_POPUP_MARGIN,
    finish_pixel_menu,
    setup_pixel_theme,
    uses_arbata,
)
from tuxemon.menu.theme import get_theme
from tuxemon.menu.transitions import PopInClamped
from tuxemon.session import local_session

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient


class SetLanguage(PygameMenuState):
    """
    This state is responsible for setting the input keys.
    This only works for pygame events.
    """

    name: ClassVar[str] = "SetLanguage"

    def __init__(
        self, client: BaseClient, main_menu: bool, **kwargs: Any
    ) -> None:
        self.main_menu = main_menu
        scale = client.context.scaling.scale_int(1)
        locale = client.config.locale
        # Arbata is drawn at its pixel size, so the menu can sit on the
        # nominal pixel grid; other locales' fonts can't. (The language
        # names are in this locale's language, so its font covers them.)
        self.pixel_perfect = uses_arbata(locale)

        super().__init__(
            client=client,
            transition=PopInClamped(
                grid=scale if self.pixel_perfect else None,
                margin=ARBATA_POPUP_MARGIN,
            ),
            **kwargs,
        )

        # Copy: changing the shared theme would affect every later menu.
        theme = get_theme(self.client.context.scaling).copy()
        theme.scrollarea_position = POSITION_EAST
        theme.widget_alignment = ALIGN_CENTER
        if self.pixel_perfect:
            setup_pixel_theme(theme, locale, self.font_type, scale)
        self._menu_config["theme"] = theme

        self.initialize_items(self.menu)
        if self.pixel_perfect:
            finish_pixel_menu(self.menu, scale, ARBATA_POPUP_MARGIN)
        self.reset_theme()

    def change_language(self, locale: str) -> None:
        T.change_language(locale)
        self.client.config.update_locale(locale)
        self.client.remove_state_by_name("SetLanguage")
        if self.main_menu:
            self.client.remove_state_by_name("ControlState")
            self.client.replace_state("StartState")
        else:
            self.client.remove_state_by_name("ControlState")
            self.client.replace_state(
                "WorldMenuState",
                menu_manager=local_session.world.menu_manager,
                character=local_session.player,
            )

    def initialize_items(self, menu: Menu) -> None:
        used = self.client.config.locale.slug
        languages = T.get_available_languages()
        for language in languages:
            if language != "README.md" and language != used:
                menu.add.button(
                    title=T.translate(f"language_{language.lower()}"),
                    action=partial(self.change_language, language),
                    # Arbata has one (pixel) size, set by the theme.
                    font_size=(
                        self.font_type.arbata
                        if self.pixel_perfect
                        else self.font_type.small
                    ),
                )
