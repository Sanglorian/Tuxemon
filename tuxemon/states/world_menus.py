# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from pygame_menu.menu import Menu

from tuxemon.constants.asset_loader import fetch_asset
from tuxemon.menu.menu import PygameMenuState
from tuxemon.menu.theme import TuxemonArrowSelection, get_theme
from tuxemon.menu.transitions import SlideRight
from tuxemon.platform.const import buttons
from tuxemon.platform.const.graphics import DIMGRAY_COLOR
from tuxemon.platform.events import PlayerInput
from tuxemon.states.monster_menu import MonsterMenuHandler

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.entity.npc import NPC
    from tuxemon.world.manager import MenuItem, WorldMenuManager

logger = logging.getLogger(__name__)


WorldMenuGameObj = Callable[[], object]


def add_menu_items_to_pygame_menu(
    menu: Menu,
    items: list[MenuItem],
    resolution: tuple[int, int],
    font_name: str | None = None,
    font_size: int | None = None,
    padding: tuple[int, int] | None = None,
) -> None:
    """Helper function to add items to a pygame_menu.Menu instance."""
    menu.clear()

    # Only forward padding when set; pygame_menu falls back to the theme
    # value when the kwarg is absent, but rejects an explicit None.
    common: dict[str, Any] = {"font_name": font_name, "font_size": font_size}
    if padding is not None:
        common["padding"] = padding

    for item in items:
        label = item.label
        callback = item.callback
        if item.enabled:
            menu.add.button(label, callback, **common)
        else:
            menu.add.label(label, font_color=DIMGRAY_COLOR, **common)

    width, height = resolution
    widgets_size = menu.get_size(widget=True)
    b_width, b_height = menu.get_scrollarea().get_border_size()
    menu.resize(
        widgets_size[0],
        height - 2 * b_height,
        position=(width + b_width, b_height, False),
    )


class WorldMenuState(PygameMenuState):
    """Menu for the world state."""

    name: ClassVar[str] = "WorldMenuState"

    def __init__(
        self,
        client: BaseClient,
        menu_manager: WorldMenuManager,
        character: NPC,
        **kwargs: Any,
    ) -> None:
        """Initialize menu state and build menu separately."""
        self.char = character
        width, height = client.context.resolution

        super().__init__(
            client=client, height=height, transition=SlideRight(), **kwargs
        )

        # Use a World-Menu-only theme whose cursor sits 2 nominal pixels lower
        # than the shared default, to line up with the taller Arbata items.
        # Must be set before the menu is first built (in update_menu_from_manager).
        scaling = self.client.context.scaling
        scale_factor = max(scaling.scale_int(1), 1)
        theme = get_theme(scaling).copy()
        theme.widget_selection_effect = TuxemonArrowSelection(
            scale_factor, y_offset_nominal=2
        )
        self._menu_config["theme"] = theme

        self.menu_manager = menu_manager
        self.menu_manager.set_menu_renderer(self)
        self.update_menu_from_manager()
        self.handler = MonsterMenuHandler(self.client, self.char.party)

    def update_menu_from_manager(self) -> None:
        """Refreshes the menu display using items provided by the manager."""
        display = self.menu_manager.build_current_menu_items(self.char)
        resolution = self.client.context.resolution
        font_name = fetch_asset("font", "Arbata.ttf")
        # Arbata's glyphs fill only three-quarters of its point size, so the
        # bitmap-tuned huge size is scaled up by 4/3 (see arbata_huge_size) to
        # make one Arbata pixel map to one grid pixel.
        font_size = self.font_type.arbata_huge
        # Tighten the vertical gap (top/bottom padding) so all entries fit on
        # screen at this larger font size; (4, 20) is (top&bottom, left&right).
        padding = (4, 20)
        add_menu_items_to_pygame_menu(
            self.menu, display, resolution, font_name, font_size, padding
        )

    def open_monster_menu(self) -> None:
        self.handler.open_monster_menu()

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        if (
            event.button in (buttons.START, buttons.B, buttons.BACK)
            and event.pressed
        ):
            self.client.pop_state()
            return None
        return super().process_event(event)
