# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
import types
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from pygame_menu.locals import ALIGN_LEFT
from pygame_menu.menu import Menu
from pygame_menu.utils import make_surface

from tuxemon.config import LOCALE_FONT_MAP
from tuxemon.menu.menu import PygameMenuState
from tuxemon.menu.theme import TuxemonArrowSelection, get_theme
from tuxemon.menu.transitions import SlideRight
from tuxemon.platform.const import buttons
from tuxemon.platform.const.graphics import DIMGRAY_COLOR
from tuxemon.platform.events import PlayerInput
from tuxemon.states.monster_menu import MonsterMenuHandler
from tuxemon.tools import transform_resource_filename

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.entity.npc import NPC
    from tuxemon.world.manager import MenuItem, WorldMenuManager

logger = logging.getLogger(__name__)


WorldMenuGameObj = Callable[[], object]

# Colour of the Esc menu's pixel shadow (#d8d8d8).
PIXEL_SHADOW_COLOR = (216, 216, 216)


def add_menu_items_to_pygame_menu(
    menu: Menu, items: list[MenuItem], resolution: tuple[int, int], scale: int
) -> None:
    """Helper function to add items to a pygame_menu.Menu instance."""
    menu.clear()

    for item in items:
        label = item.label
        callback = item.callback
        if item.enabled:
            menu.add.button(label, callback)
        else:
            menu.add.label(
                label,
                font_color=DIMGRAY_COLOR,
            )

    render = pixel_shadow_renderer(scale)
    for widget in menu.get_widgets():
        widget._render_string = types.MethodType(render, widget)
        widget._force_render()

    width, height = resolution
    widgets_size = menu.get_size(widget=True)
    b_width, b_height = menu.get_scrollarea().get_border_size()
    menu.resize(
        widgets_size[0],
        height - 2 * b_height,
        position=(width + b_width, b_height, False),
    )
    spread_on_pixel_grid(menu, height - 2 * b_height, scale)


def pixel_shadow_renderer(scale: int) -> Callable[..., Any]:
    """A pygame_menu text renderer with a 3-layer, 1 nominal px drop shadow.

    The shadow is three copies of the text in the shadow colour: 1 nominal px
    down, 1 down and right, and 1 right, so it stays on the pixel grid and
    has no gaps along diagonal strokes.
    """
    offsets = ((0, scale), (scale, scale), (scale, 0))

    def render(widget: Any, string: str, color: Any) -> Any:
        text = widget._font_render_string(string, color)
        shadow = widget._font_render_string(string, PIXEL_SHADOW_COLOR)
        surface = make_surface(
            text.get_width() + scale, text.get_height() + scale, alpha=True
        )
        for offset in offsets:
            surface.blit(shadow, offset)
        surface.blit(text, (0, 0))
        return surface

    return render


def spread_on_pixel_grid(menu: Menu, menu_height: int, scale: int) -> None:
    """Spread the entries evenly down the menu, in whole nominal pixels.

    This does what vertical fills would, but fills split the spare space
    into fractions of a nominal pixel, which blurs the grid. Instead every
    entry gets the same whole-pixel pitch (the largest that fits) and the
    block is centred, also on the grid.
    """
    widgets = menu.get_widgets()
    if not widgets:
        return
    entry_height = widgets[0].get_height()
    available = menu_height // scale
    pitch = available // len(widgets)
    block = (len(widgets) - 1) * pitch * scale + entry_height
    top = (available - block // scale) // 2

    menu._auto_centering = False
    for widget in widgets:
        widget.set_margin(0, pitch * scale - entry_height)
        # pygame_menu starts each column 1 screen px down; take it back off.
        widget.translate(0, top * scale - 1)
    menu.render()


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

        # The Esc menu uses Arbata on a private copy of the theme, so other
        # menus keep their font. It must be set before the menu is built.
        # Locales with their own font (e.g. CJK, which Arbata lacks) keep it.
        locale = self.client.config.locale
        if locale.font_file == LOCALE_FONT_MAP["default"][0]:
            scale_int = self.client.context.scaling.scale_int
            theme = get_theme(self.client.context.scaling).copy()
            theme.widget_font = transform_resource_filename(
                "font", locale.arbata_font_file
            )
            theme.widget_font_size = self.font_type.arbata
            # The shared theme's shadow is offset a fixed 2 screen px, off
            # the nominal grid at most scales; the entries draw their own
            # (see pixel_shadow_renderer) instead.
            theme.widget_font_shadow = False
            # Set explicitly: other screens can change the shared theme's
            # alignment, and this copy is taken each time the menu opens.
            theme.widget_alignment = ALIGN_LEFT
            # Arbata capitals sit 6 nominal px into each entry (2 px padding
            # plus 4 px above the capitals); lower the 9 px cursor 5 px.
            theme.widget_selection_effect = TuxemonArrowSelection(
                scale_int(1), y_offset_nominal=5
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
        scale = self.client.context.scaling.scale_int(1)
        add_menu_items_to_pygame_menu(self.menu, display, resolution, scale)

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
