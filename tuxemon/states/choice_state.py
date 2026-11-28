# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from pygame.rect import Rect
from pygame_menu.locals import ALIGN_LEFT, POSITION_EAST

from tuxemon.config import LOCALE_FONT_MAP
from tuxemon.menu.menu import PygameMenuState
from tuxemon.menu.theme import TuxemonArrowSelection, get_theme
from tuxemon.menu.transitions import PopInClamped
from tuxemon.platform.const.sizes import NATIVE_RESOLUTION
from tuxemon.tools import transform_resource_filename
from tuxemon.ui.menu_options import MenuOptions

if TYPE_CHECKING:
    from pygame_menu.menu import Menu

    from tuxemon.base_client import BaseClient
    from tuxemon.prepare import DisplayContext

# Arbata choice layout, in nominal pixels, inside the box's border: options
# 12 px apart, their text 10 px in from the left with the arrow cursor 2 px
# in, and the first option's capitals 2 px below the top. Arbata's capitals
# start 4 px into its line box and are 8 px tall; the 10 px arrow sits 1 px
# above and below them.
CHOICE_PITCH = 12
CHOICE_ARROW_LEFT = 2
CHOICE_TEXT_LEFT = 10
CHOICE_RIGHT_PADDING = 2
CHOICE_CAP_TOP = 2
CHOICE_BOTTOM_PADDING = 2
CHOICE_CAP_HEIGHT = 8
CHOICE_DESCENDER = 2
ARBATA_CAP_TOP = 4
CHOICE_ARROW_OFFSET = ARBATA_CAP_TOP - 1
# Width of the border drawn around the menu (a third of the border image).
CHOICE_BORDER = 6


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

        super().__init__(
            client=client,
            transition=PopInClamped(
                max_height_percentage=self.config.max_height_percentage
            ),
            **kwargs,
        )

        theme = get_theme(self.client.context.scaling).copy()

        # Short lists in the default locale use Arbata, laid out on the pixel
        # grid. Long, scrolling lists, large GUI and locales with their own
        # font (e.g. CJK, which Arbata lacks) keep the menu font.
        locale = self.client.config.locale
        count = len(menu.options)
        self.pixel_layout = (
            not self.client.config.large_gui
            and locale.font_file == LOCALE_FONT_MAP["default"][0]
            and 0 < count <= self.config.max_elements
            and self._content_height(count) + 2 * CHOICE_BORDER
            <= NATIVE_RESOLUTION[1]
        )
        font_size = self.font_type.medium
        if self.pixel_layout:
            scale_int = self.client.context.scaling.scale_int
            font_size = self.font_type.arbata
            theme.widget_font = transform_resource_filename(
                "font", locale.arbata_font_file
            )
            theme.widget_font_shadow = False
            theme.widget_alignment = ALIGN_LEFT
            theme.widget_margin = (0, 0)
            # The padding puts the arrow, drawn just left of the widget,
            # CHOICE_ARROW_LEFT in from the box's inside.
            theme.widget_padding = (
                0,
                0,
                0,
                scale_int(CHOICE_TEXT_LEFT - CHOICE_ARROW_LEFT - 6),
            )
            theme.widget_selection_effect = TuxemonArrowSelection(
                scale_int(1), y_offset_nominal=CHOICE_ARROW_OFFSET
            )
        elif count > self.config.max_elements:
            theme.scrollarea_position = POSITION_EAST

        self._menu_config["theme"] = theme

        for option in menu.get_menu():
            self.menu.add.button(
                option.display_text,
                option.action,
                font_size=font_size,
            )

        if self.pixel_layout:
            target = self._pixel_rect()
            self.transition = PopInPixel(target, scale_int(1))
            self._place_widgets(target)

        self.escape_key_exits = escape_key_exits

    @staticmethod
    def _content_height(count: int) -> int:
        """Nominal height inside the border for ``count`` options."""
        return (
            CHOICE_CAP_TOP
            + (count - 1) * CHOICE_PITCH
            + CHOICE_CAP_HEIGHT
            + CHOICE_DESCENDER
            + CHOICE_BOTTOM_PADDING
        )

    def _pixel_rect(self) -> Rect:
        """Where the menu (inside its border) goes, in screen pixels.

        Its corner meets the dialog box's top right when a dialog is open,
        and otherwise it's centred, on whole nominal pixels.
        """
        scale = self.client.context.scaling.scale_int(1)
        widgets = self.menu.get_widgets()
        text_width = max(widget.get_width() for widget in widgets) // scale
        width = CHOICE_ARROW_LEFT + 6 + text_width + CHOICE_RIGHT_PADDING
        height = self._content_height(len(widgets))
        screen_w, screen_h = NATIVE_RESOLUTION
        dialog = next(
            (
                state
                for state in self.client.active_states
                if state.name == "DialogState"
            ),
            None,
        )
        if dialog is not None:
            box = dialog.rect
            right = box.right // scale - CHOICE_BORDER
            bottom = box.top // scale - CHOICE_BORDER
            left, top = right - width, bottom - height
        else:
            left = (screen_w - width) // 2
            top = (screen_h - height) // 2
        return Rect(left * scale, top * scale, width * scale, height * scale)

    def _place_widgets(self, target: Rect) -> None:
        """Put each option's line box on its nominal row."""
        menu = self.menu
        scale = self.client.context.scaling.scale_int(1)
        menu._auto_centering = False
        menu.resize(
            target.width,
            target.height,
            position=(target.left, target.top, False),
        )
        menu.render()
        for index, widget in enumerate(menu.get_widgets()):
            rect = widget.get_rect(to_real_position=True)
            want_x = target.left + scale * (CHOICE_ARROW_LEFT + 6)
            want_y = target.top + scale * (
                CHOICE_CAP_TOP - ARBATA_CAP_TOP + index * CHOICE_PITCH
            )
            dx, dy = widget.get_translate()
            widget.translate(dx + want_x - rect.left, dy + want_y - rect.top)
        menu.render()


class PopInPixel:
    """Zoom the menu in from its centre to ``target``, in whole nominal
    pixels, so every frame stays on the pixel grid."""

    def __init__(self, target: Rect, scale: int) -> None:
        self.target = target
        self.scale = scale

    def apply(
        self, menu: Menu, progress: float, context: DisplayContext
    ) -> None:
        s = self.scale
        progress = max(0.0, min(1.0, progress))
        width = max(s, int(self.target.width * progress) // s * s)
        height = max(s, int(self.target.height * progress) // s * s)
        left = (self.target.centerx - width // 2) // s * s
        top = (self.target.centery - height // 2) // s * s
        if progress >= 1.0:
            left, top = self.target.topleft
            width, height = self.target.size
        menu.resize(width, height, position=(left, top, False))
