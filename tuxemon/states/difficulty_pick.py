# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar

from pygame_menu.locals import ALIGN_CENTER
from pygame_menu.widgets.selection.highlight import HighlightSelection

from tuxemon.locale.locale import T
from tuxemon.menu.menu import PygameMenuState
from tuxemon.menu.pixel_grid import (
    ARBATA_COMPACT_MARGIN,
    ARBATA_COMPACT_UNDERLINE_ROW,
    add_pixel_underline,
    apply_arbata,
    apply_pixel_shadow,
    keep_on_grid,
    setup_pixel_scrolling,
    uses_arbata,
)
from tuxemon.menu.theme import get_theme

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient

DIFFICULTIES = ["beginner", "easy", "normal", "hard", "expert"]


class DifficultyPickState(PygameMenuState):
    """Generic difficulty selection state."""

    name: ClassVar[str] = "DifficultyPickState"

    def __init__(
        self,
        client: BaseClient,
        on_pick: Callable[[str], None],
        difficulties: list[str] = DIFFICULTIES,
        **kwargs: Any,
    ) -> None:
        width, height = client.context.resolution
        super().__init__(client=client, height=height, width=width, **kwargs)

        self.scale = client.context.scaling.scale_int(1)
        locale = client.config.locale
        # Arbata is drawn at its pixel size, so the menu can sit on the
        # nominal pixel grid; other locales' fonts can't.
        self.pixel_perfect = uses_arbata(locale)
        if self.pixel_perfect:
            theme = get_theme(client.context.scaling).copy()
            apply_arbata(theme, locale, self.font_type, self.scale, True)
            setup_pixel_scrolling(theme, self.scale)
            self._menu_config["theme"] = theme

        self.on_pick = on_pick
        self.difficulties = difficulties
        self._build_menu()
        if self.pixel_perfect:
            apply_pixel_shadow(self.menu.get_widgets(), self.scale)
            add_pixel_underline(
                self.title, self.scale, ARBATA_COMPACT_UNDERLINE_ROW
            )
            keep_on_grid(self.menu, self.scale)
        self.reset_theme()

    def _build_menu(self) -> None:
        title = T.translate("choose_difficulty")
        if self.pixel_perfect:
            self.title: Any = self.menu.add.label(
                title=title,
                align=ALIGN_CENTER,
                # A little more space under the title than between entries.
                margin=(0, self.scale * (ARBATA_COMPACT_MARGIN + 4)),
            )
        else:
            self.menu.add.label(
                title=title,
                font_size=self.font_type.big,
                align=ALIGN_CENTER,
                underline=True,
            )

        for level in self.difficulties:
            if self.pixel_perfect:
                # A 1 nominal px box, 1 px out from each side of the entry.
                selection = HighlightSelection(
                    border_width=self.scale,
                    margin_x=2 * self.scale,
                    margin_y=0,
                )
                self.menu.add.button(
                    title=T.translate(f"level_{level}"),
                    action=partial(self._handle_pick, level),
                    button_id=f"diff_{level}",
                    selection_effect=selection,
                    align=ALIGN_CENTER,
                    margin=(0, self.scale * ARBATA_COMPACT_MARGIN),
                )
            else:
                self.menu.add.button(
                    title=T.translate(f"level_{level}"),
                    action=partial(self._handle_pick, level),
                    button_id=f"diff_{level}",
                    font_size=self.font_type.medium,
                    selection_effect=HighlightSelection(),
                    align=ALIGN_CENTER,
                )

    def _handle_pick(self, difficulty: str) -> None:
        self.on_pick(difficulty)
