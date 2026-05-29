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
from tuxemon.platform.const.graphics import (
    BG_JOURNAL_CHOICE,
    DIMGRAY_COLOR,
    FONT_SHADOW_COLOR,
)
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
        arbata = transform_resource_filename("font", "Arbata.ttf")
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

        # Pixel-perfect drop shadow: draw a copy of the text in the shadow
        # colour first (so it sits on a lower z level) offset by 1 nominal
        # pixel right and down, then the real text on top. Both are whole-pixel
        # blits of crisp glyph surfaces, so the result stays pixel-perfect.
        shadow_offset = scale_int(1)

        def add_shadowed_label(
            title: str, font_name: str, font_size: int, x: int, y: int
        ) -> None:
            menu.add.label(
                title=title,
                font_size=font_size,
                font_name=font_name,
                font_color=FONT_SHADOW_COLOR,
                float=True,
                float_origin_position=True,
                padding=0,
            ).translate(x + shadow_offset, y + shadow_offset)
            menu.add.label(
                title=title,
                font_size=font_size,
                font_name=font_name,
                float=True,
                float_origin_position=True,
                padding=0,
            ).translate(x, y)

        biggest = self.font_type.biggest
        huge = biggest * 2
        add_shadowed_label(
            featured_text, minimal_font, biggest, scale_int(3), scale_int(96)
        )
        add_shadowed_label(
            str(featured), arbata, huge, scale_int(10), scale_int(102)
        )
        add_shadowed_label(
            stubs_text, minimal_font, biggest, scale_int(3), scale_int(112)
        )
        add_shadowed_label(
            str(stubs), arbata, huge, scale_int(10), scale_int(118)
        )
        add_shadowed_label(
            missing_text, minimal_font, biggest, scale_int(3), scale_int(128)
        )
        add_shadowed_label(
            str(missing), arbata, huge, scale_int(10), scale_int(134)
        )

        btn_x_offset = scale_int(44)
        btn_y_offset = scale_int(8)
        menu._column_max_width = [scale_int(115), scale_int(150)]

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
                    font_size=self.font_type.biggest * 2,
                    font_name=arbata,
                ).translate(btn_x_offset, btn_y_offset)
            else:
                lab1: Any = menu.add.label(
                    label,
                    font_color=DIMGRAY_COLOR,
                    font_size=self.font_type.biggest * 2,
                    font_name=arbata,
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
        self._menu_config["theme"] = theme

        self.add_menu_items(self.menu, box)
        self.reset_theme()
