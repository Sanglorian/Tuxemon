# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from pygame import SRCALPHA, draw
from pygame.rect import Rect
from pygame.surface import Surface
from pygame_menu.locals import ALIGN_CENTER
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
    # Number of sprites per row.
    columns: int = 3
    # Horizontal gap (unscaled px) between sprite cells.
    column_gap: int = 8
    # Vertical separation (unscaled px) between rows.
    row_gap: int = 4
    # How much of the neighbouring row (unscaled px) peeks past the active
    # row when there is more than one row.
    row_peek: int = 8
    # Padding (unscaled px) of the selection cursor around the active sprite.
    cursor_padding: int = 5


@dataclass
class _Choice:
    name: str
    sprite: Surface
    callback: Callable[[], None]


class ChoiceNpc(PygameMenuState):
    """
    Appearance picker: a grid of sprites with the active row centred.

    The options are laid out in rows of ``columns``. The row containing the
    current selection is centred in the frame and the neighbouring row peeks
    in above or below. Left/right moves within the grid, up/down jumps a row,
    and "Select" (or the confirm button) stores the chosen option key in the
    target variable, so the downstream events are unchanged.
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

        cols = max(1, min(self.config.columns, len(self._choices)))
        self._columns = cols
        self._rows = math.ceil(len(self._choices) / cols)

        scale = self.client.context.scaling.scale_int
        self._col_gap = scale(self.config.column_gap)
        self._row_gap = scale(self.config.row_gap)
        self._row_peek = scale(self.config.row_peek)
        self._cursor_pad = scale(self.config.cursor_padding)
        self._cell_w = (
            max(c.sprite.get_width() for c in self._choices) + self._col_gap
        )
        self._cell_h = max(c.sprite.get_height() for c in self._choices)

        theme = get_theme(self.client.context.scaling).copy()
        self._menu_config["theme"] = theme

        self._build_menu()

        self.escape_key_exits = escape_key_exits

    def _build_choices(self, menu: MenuOptions) -> list[_Choice]:
        choices: list[_Choice] = []
        for option in menu.get_menu():
            npc = NpcModel.lookup(option.key, db)
            sheet = get_combat_sheet(npc.template)
            sprite = scale_surface(
                sheet.front(), self.factor * self.config.scale_sprite
            )
            # An option whose label was never translated falls back to its
            # own key; show a placeholder rather than the raw slug.
            name = option.display_text
            if name == option.key:
                name = "???"
            choices.append(_Choice(name, sprite, option.action))
        return choices

    def _build_menu(self) -> None:
        self._image_widget = self.menu.add.image(
            self._create_image_from_surface(self._compose()),
            align=ALIGN_CENTER,
        )
        self._name_label = self.menu.add.label(
            self._choices[self._index].name,
            font_size=self.font_type.small,
            align=ALIGN_CENTER,
        )
        self.menu.add.vertical_margin(
            self.client.context.scaling.scale_int(self.config.row_gap)
        )
        confirm = self.menu.add.button(
            T.translate("menu_select"),
            self._confirm,
            font_size=self.font_type.small,
            align=ALIGN_CENTER,
            selection_effect=HighlightSelection(),
        )
        self.menu.select_widget(confirm)

    def _compose(self) -> Surface:
        """Render the grid with the active row centred into one surface."""
        cell_w, cell_h = self._cell_w, self._cell_h
        row_pitch = cell_h + self._row_gap
        active_row = self._index // self._columns

        surf_w = self._columns * cell_w
        if self._rows > 1:
            surf_h = cell_h + 2 * (self._row_gap + self._row_peek)
        else:
            surf_h = cell_h
        surface = Surface((surf_w, surf_h), SRCALPHA)
        centre_y = surf_h // 2

        for idx, choice in enumerate(self._choices):
            row, col = divmod(idx, self._columns)
            cx = col * cell_w + cell_w // 2
            cy = centre_y + (row - active_row) * row_pitch
            sprite = choice.sprite
            if row != active_row:
                sprite = sprite.copy()
                sprite.set_alpha(110)
            if idx == self._index:
                self._draw_cursor(surface, (cx, cy))
            surface.blit(sprite, sprite.get_rect(center=(cx, cy)))
        return surface

    def _draw_cursor(self, surface: Surface, center: tuple[int, int]) -> None:
        pad = self._cursor_pad
        rect = Rect(
            0,
            0,
            self._cell_w - self._col_gap + 2 * pad,
            self._cell_h + 2 * pad,
        )
        rect.center = center
        fill = Surface(rect.size, SRCALPHA)
        fill.fill((250, 230, 120, 70))
        surface.blit(fill, rect)
        draw.rect(surface, (250, 220, 90), rect, width=max(2, pad // 2))

    def _refresh(self) -> None:
        # Swap the composed grid and the name. The menu rebuilds its surface
        # on the next draw; calling render() explicitly leaves it stale.
        self._image_widget.set_image(
            self._create_image_from_surface(self._compose())
        )
        self._name_label.set_title(self._choices[self._index].name)

    def _move(self, delta: int) -> None:
        # Wrap within the active row so left/right never changes the row.
        row, col = divmod(self._index, self._columns)
        row_start = row * self._columns
        row_len = min(self._columns, len(self._choices) - row_start)
        self._index = row_start + (col + delta) % row_len
        self._refresh()

    def _move_row(self, delta: int) -> None:
        if self._rows <= 1:
            return
        target = self._index + delta * self._columns
        # Wrap vertically, keeping the column where possible.
        self._index = target % len(self._choices)
        self._refresh()

    def _confirm(self) -> None:
        self._choices[self._index].callback()

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        if not self.valid_press(event):
            return super().process_event(event)
        if event.button == buttons.LEFT:
            self._move(-1)
            return None
        if event.button == buttons.RIGHT:
            self._move(1)
            return None
        if event.button == buttons.UP:
            self._move_row(-1)
            return None
        if event.button == buttons.DOWN:
            self._move_row(1)
            return None
        return super().process_event(event)
