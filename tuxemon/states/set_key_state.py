# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pygame_menu.locals import ALIGN_CENTER, POSITION_EAST

from tuxemon.locale.locale import T
from tuxemon.menu.menu import PygameMenuState
from tuxemon.menu.pixel_grid import (
    finish_pixel_menu,
    setup_pixel_theme,
    uses_arbata,
)
from tuxemon.menu.theme import get_theme
from tuxemon.menu.transitions import PopInClamped
from tuxemon.platform.platform_pygame.events import KeyBindingRules

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.platform.events import PlayerInput


class SetKeyState(PygameMenuState):
    """
    This state is responsible for setting the input keys.
    This only works for pygame events.
    """

    name: ClassVar[str] = "SetKeyState"

    def __init__(self, client: BaseClient, value: str, **kwargs: Any) -> None:
        self.value = value
        scale = client.context.scaling.scale_int(1)
        locale = client.config.locale
        # Arbata is drawn at its pixel size, so the menu can sit on the
        # nominal pixel grid; other locales' fonts can't.
        pixel_perfect = uses_arbata(locale)

        super().__init__(
            client=client,
            transition=PopInClamped(grid=scale if pixel_perfect else None),
            **kwargs,
        )

        # Copy: changing the shared theme would affect every later menu.
        theme = get_theme(self.client.context.scaling).copy()
        theme.scrollarea_position = POSITION_EAST
        theme.widget_alignment = ALIGN_CENTER
        if pixel_perfect:
            setup_pixel_theme(theme, locale, self.font_type, scale)
        self._menu_config["theme"] = theme

        self.menu.add.label(
            T.translate("options_new_input_key0").upper(),
            # Arbata has one (pixel) size, set by the theme.
            font_size=(
                self.font_type.arbata
                if pixel_perfect
                else self.font_type.small
            ),
        )
        if pixel_perfect:
            # No cursor here, so the label's padding is margin enough.
            finish_pixel_menu(self.menu, scale)
        self.reset_theme()

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        """
        Accepts a PlayerInput event and binds the first valid keycode.
        Assumes event.value is already normalized by InputConfig.
        """
        if not event.pressed:
            return None

        pressed_key = self.client.config.input.normalize_key(event.value)

        if pressed_key is None:
            return None  # ignore unmappable input

        if KeyBindingRules.is_valid_binding(pressed_key):
            self.client.remove_state_by_name("SetKeyState")
            self.client.config.update_control(self.value, pressed_key)

            keyboard = self.client.input_manager.core_devices.keyboard
            if keyboard is not None:
                keyboard.reload_mapping(
                    self.client.config.input.keyboard_button_map
                )

            return None

        return None
