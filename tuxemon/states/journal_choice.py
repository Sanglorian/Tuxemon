# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import math
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar

from pygame_menu.locals import ALIGN_LEFT, POSITION_EAST
from pygame_menu.menu import Menu

from tuxemon.database.runtime import db
from tuxemon.db import MonsterModel
from tuxemon.locale.locale import T
from tuxemon.menu.menu import PygameMenuState
from tuxemon.menu.pixel_grid import (
    ARBATA_CURSOR_OFFSET,
    arbata_font,
    keep_on_grid,
    uses_arbata,
)
from tuxemon.menu.theme import TuxemonArrowSelection
from tuxemon.platform.const.graphics import BG_JOURNAL_CHOICE, DIMGRAY_COLOR
from tuxemon.tools import transform_resource_filename

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.entity.npc import NPC

MAX_PAGE = 20


MenuGameObj = Callable[[], object]


class JournalChoice(PygameMenuState):
    """Shows journal (screen 1/3)."""

    name: ClassVar[str] = "JournalChoice"

    def add_menu_items(
        self,
        menu: Menu,
        monsters: list[MonsterModel],
    ) -> None:

        def change_state(state: str, **kwargs: Any) -> MenuGameObj:
            return partial(self.client.push_state, state, **kwargs)

        total_monster = len(monsters)
        pages = math.ceil(total_monster / MAX_PAGE)

        # floating count badges
        minimal_font = transform_resource_filename(
            "font", self.client.config.locale.minimal_font_file
        )
        thin_font = transform_resource_filename(
            "font", self.client.config.locale.thin_font_file
        )
        valid_slugs = {mon.slug for mon in monsters}
        featured = sum(
            1 for slug in valid_slugs if self.char.tuxepedia.is_caught(slug)
        )
        stubs = sum(
            1 for slug in valid_slugs if self.char.tuxepedia.is_seen(slug)
        )
        missing = total_monster - featured - stubs

        menu._auto_centering = False
        scale_int = self.client.context.scaling.scale_int

        featured_text = T.format("journal_badge_featured", {"n": ""}).rstrip()
        stubs_text = T.format("journal_badge_stubs", {"n": ""}).rstrip()
        missing_text = T.format("journal_badge_missing", {"n": ""}).rstrip()

        badge_featured_lbl: Any = menu.add.label(
            title=featured_text,
            font_size=self.font_type.biggest,
            font_name=minimal_font,
            float=True,
            float_origin_position=True,
            padding=0,
        )
        badge_featured_lbl.translate(scale_int(3), scale_int(96))

        badge_featured_num: Any = menu.add.label(
            title=str(featured),
            font_size=self.font_type.biggest,
            font_name=thin_font,
            float=True,
            float_origin_position=True,
            padding=0,
        )
        badge_featured_num.translate(scale_int(10), scale_int(102))

        badge_stubs_lbl: Any = menu.add.label(
            title=stubs_text,
            font_size=self.font_type.biggest,
            font_name=minimal_font,
            float=True,
            float_origin_position=True,
            padding=0,
        )
        badge_stubs_lbl.translate(scale_int(3), scale_int(112))

        badge_stubs_num: Any = menu.add.label(
            title=str(stubs),
            font_size=self.font_type.biggest,
            font_name=thin_font,
            float=True,
            float_origin_position=True,
            padding=0,
        )
        badge_stubs_num.translate(scale_int(10), scale_int(118))

        badge_missing_lbl: Any = menu.add.label(
            title=missing_text,
            font_size=self.font_type.biggest,
            font_name=minimal_font,
            float=True,
            float_origin_position=True,
            padding=0,
        )
        badge_missing_lbl.translate(scale_int(3), scale_int(128))

        badge_missing_num: Any = menu.add.label(
            title=str(missing),
            font_size=self.font_type.biggest,
            font_name=thin_font,
            float=True,
            float_origin_position=True,
            padding=0,
        )
        badge_missing_num.translate(scale_int(10), scale_int(134))

        btn_x_offset = scale_int(44)
        btn_y_offset = scale_int(8)
        menu._column_max_width = [scale_int(115), scale_int(150)]

        # The page list is in Arbata, like the pages it leads to (see
        # JournalState), except in locales with their own font.
        page_font: dict[str, Any] = {"font_size": self.font_type.biggest}
        if self.pixel_perfect:
            page_font = {
                "font_size": self.font_type.arbata,
                "font_name": arbata_font(self.client.config.locale),
                # Pull entries 5 nominal px closer together than the theme
                # spacing, as on the journal pages.
                "margin": (0, -scale_int(5)),
            }

        for page in range(pages):
            start = page * MAX_PAGE
            end = min(start + MAX_PAGE, total_monster)
            tuxepedia = [
                mon
                for mon in monsters
                if start < mon.txmn_id <= end
                and self.char.tuxepedia.is_registered(mon.slug)
            ]
            label = T.format(
                "page_tuxepedia", {"a": str(start + 1), "b": str(end)}
            ).upper()

            if tuxepedia:
                menu.add.button(
                    label,
                    change_state(
                        "JournalState",
                        character=self.char,
                        monsters=monsters,
                        page=page,
                    ),
                    **page_font,
                ).translate(btn_x_offset, btn_y_offset)
            else:
                lab1: Any = menu.add.label(
                    label,
                    font_color=DIMGRAY_COLOR,
                    **page_font,
                )
                lab1.translate(btn_x_offset, btn_y_offset)

    def __init__(
        self, client: BaseClient, character: NPC, **kwargs: Any
    ) -> None:
        self.char = character

        MonsterModel.load_cache(db)
        cache = MonsterModel.get_cache()

        width, height = client.context.resolution

        columns = 2

        box = list(cache.values())
        diff = round(len(box) / MAX_PAGE) + 1
        rows = int(diff / columns) + 1

        super().__init__(
            client=client,
            height=height,
            width=width,
            columns=columns,
            rows=rows,
            **kwargs,
        )

        theme = self._setup_theme(BG_JOURNAL_CHOICE)
        theme.widget_font_shadow = False
        theme.scrollarea_position = POSITION_EAST
        theme.widget_alignment = ALIGN_LEFT
        scale = client.context.scaling.scale_int(1)
        self.pixel_perfect = uses_arbata(client.config.locale)
        if self.pixel_perfect:
            # Arbata capitals sit 6 nominal px into each entry (2 px padding
            # plus 4 px above the capitals); lower the cursor 5 px to match.
            theme.widget_selection_effect = TuxemonArrowSelection(
                scale, y_offset_nominal=ARBATA_CURSOR_OFFSET
            )
            # Arbata is drawn at its pixel size, so it needs no anti-aliasing.
            theme.widget_font_antialias = False  # type: ignore[assignment]
        self._menu_config["theme"] = theme

        self.add_menu_items(self.menu, box)
        if self.pixel_perfect:
            # pygame_menu centres each column (and starts it 1 screen px
            # down), which leaves the list off the nominal grid.
            keep_on_grid(self.menu, scale, center=False)
        self.reset_theme()
