# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from pygame import SRCALPHA
from pygame.surface import Surface
from pygame_menu.baseimage import BaseImage
from pygame_menu.locals import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    POSITION_CENTER,
)
from pygame_menu.widgets.selection.highlight import HighlightSelection

from tuxemon.database.runtime import db
from tuxemon.db import NpcModel
from tuxemon.entity.sheet import get_combat_sheet
from tuxemon.graphics import scale_surface
from tuxemon.locale.locale import T
from tuxemon.menu.menu import PygameMenuState
from tuxemon.menu.theme import get_theme
from tuxemon.menu.transitions import PopInClamped
from tuxemon.platform.const import buttons
from tuxemon.ui.menu_options import MenuOptions

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.platform.events import PlayerInput


@dataclass
class MenuNpcConfig:
    # Fraction of the screen height the picker is allowed to occupy.
    max_height_percentage: float = 0.8
    # Scale applied to each appearance sprite, on top of the display factor.
    scale_sprite: float = 1.0
    # Horizontal gap (unscaled px) between each arrow and the sprite.
    arrow_gap: int = 30
    # Extra room (unscaled px) added to the arrow frame so the sprite clears
    # the frame's internal padding (the height check is strict).
    frame_buffer: int = 24
    # Vertical spacing (unscaled px) between the sprite row and the buttons.
    row_spacing: int = 15


@dataclass
class _Choice:
    name: str
    image: BaseImage
    callback: Callable[[], None]


class ChoiceNpc(PygameMenuState):
    """
    Appearance picker: a single centred sprite flanked by arrows.

    The player cycles through the options with the left/right keys (or the
    on-screen arrow buttons) and confirms the current one with "Select".
    Confirming still stores the option key in the target variable, so the
    downstream events are unchanged.
    """

    name: ClassVar[str] = "ChoiceNpc"

    def __init__(
        self,
        client: BaseClient,
        menu: MenuOptions,
        escape_key_exits: bool = False,
        config: MenuNpcConfig | None = None,
        **kwargs: Any,
    ) -> None:
        self.config = config or MenuNpcConfig()

        super().__init__(
            client=client,
            transition=PopInClamped(
                max_height_percentage=self.config.max_height_percentage,
            ),
            **kwargs,
        )

        self._index = 0
        self._choices = self._build_choices(menu)

        theme = get_theme(self.client.context.scaling).copy()
        self._menu_config["theme"] = theme

        self._build_carousel()

        self.escape_key_exits = escape_key_exits

    def _build_choices(self, menu: MenuOptions) -> list[_Choice]:
        # First pass: render every sprite and find the common canvas size.
        rendered: list[tuple[str, Surface, Callable[[], None]]] = []
        canvas_w = canvas_h = 1
        for option in menu.get_menu():
            npc = NpcModel.lookup(option.key, db)
            sheet = get_combat_sheet(npc.template)
            scaled = scale_surface(
                sheet.front(), self.factor * self.config.scale_sprite
            )
            canvas_w = max(canvas_w, scaled.get_width())
            canvas_h = max(canvas_h, scaled.get_height())
            # An option whose label was never translated falls back to its
            # own key; show a placeholder rather than the raw slug.
            name = option.display_text
            if name == option.key:
                name = "???"
            rendered.append((name, scaled, option.action))

        # Second pass: pad every sprite onto an identically sized canvas so the
        # image widget never changes size when the selection is swapped. A
        # constant size keeps the sprite within the arrow frame, which pygame
        # menu enforces strictly.
        choices: list[_Choice] = []
        for name, scaled, action in rendered:
            canvas = Surface((canvas_w, canvas_h), SRCALPHA)
            canvas.blit(
                scaled, scaled.get_rect(center=canvas.get_rect().center)
            )
            choices.append(
                _Choice(name, self._create_image_from_surface(canvas), action)
            )
        return choices

    def _build_carousel(self) -> None:
        gap = self.client.context.scaling.scale_int(self.config.arrow_gap)
        buffer = self.client.context.scaling.scale_int(
            self.config.frame_buffer
        )

        left = self.menu.add.button(
            "<",
            self._select_previous,
            font_size=self.font_type.biggest,
            selection_effect=HighlightSelection(),
        )
        right = self.menu.add.button(
            ">",
            self._select_next,
            font_size=self.font_type.biggest,
            selection_effect=HighlightSelection(),
        )
        self._image_widget = self.menu.add.image(
            self._choices[self._index].image, align=ALIGN_CENTER
        )

        arrow_w, arrow_h = left.get_size()
        sprite_w, sprite_h = self._image_widget.get_size()
        frame_w = sprite_w + 2 * arrow_w + 2 * gap + buffer
        frame_h = max(sprite_h, arrow_h) + buffer

        frame = self.menu.add.frame_h(frame_w, frame_h, align=ALIGN_CENTER)
        frame.pack(left, align=ALIGN_LEFT, vertical_position=POSITION_CENTER)
        frame.pack(
            self._image_widget,
            align=ALIGN_CENTER,
            vertical_position=POSITION_CENTER,
        )
        frame.pack(right, align=ALIGN_RIGHT, vertical_position=POSITION_CENTER)

        self._name_label = self.menu.add.label(
            self._choices[self._index].name,
            font_size=self.font_type.small,
            align=ALIGN_CENTER,
        )
        self.menu.add.vertical_margin(
            self.client.context.scaling.scale_int(self.config.row_spacing)
        )
        confirm = self.menu.add.button(
            T.translate("menu_select"),
            self._confirm,
            font_size=self.font_type.small,
            align=ALIGN_CENTER,
            selection_effect=HighlightSelection(),
        )
        self.menu.select_widget(confirm)

    def _change_selection(self, delta: int) -> None:
        self._index = (self._index + delta) % len(self._choices)
        choice = self._choices[self._index]
        # Swap the sprite and name. The menu rebuilds its surface on the next
        # draw; calling render() explicitly here leaves the image stale.
        self._image_widget.set_image(choice.image)
        self._name_label.set_title(choice.name)

    def _select_previous(self) -> None:
        self._change_selection(-1)

    def _select_next(self) -> None:
        self._change_selection(1)

    def _confirm(self) -> None:
        self._choices[self._index].callback()

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        if event.button == buttons.LEFT and self.valid_press(event):
            self._select_previous()
            return None
        if event.button == buttons.RIGHT and self.valid_press(event):
            self._select_next()
            return None
        return super().process_event(event)
