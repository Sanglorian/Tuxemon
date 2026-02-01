# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pygame_menu.locals import ALIGN_CENTER, POSITION_EAST

from tuxemon.locale import T
from tuxemon.menu.menu import PygameMenuState
from tuxemon.platform.const.graphics import BG_MISSIONS
from tuxemon.platform.const.sizes import MONTH_KEYS
from tuxemon.prepare import SCREEN_SIZE


class DatePickerState(PygameMenuState):
    name = "DatePickerState"

    def __init__(
        self, callback: Callable[[tuple[int, int]], None], **kwargs: Any
    ):
        self.callback = callback
        self.selected_month: int | None = None
        width, height = SCREEN_SIZE
        escape_key_exits = kwargs.pop("escape_key_exits", None)

        theme = self._setup_theme(BG_MISSIONS)
        theme.widget_alignment = ALIGN_CENTER
        theme.scrollarea_position = POSITION_EAST
        theme.title = True

        super().__init__(width=width, height=height, **kwargs)

        if escape_key_exits is not None:
            self.escape_key_exits = escape_key_exits
        self._build_month_menu()
        self.reset_theme()

    def _build_month_menu(self) -> None:
        self.menu.clear()
        self.menu.set_title(T.translate("select_month")).center_content()

        for index, key in enumerate(MONTH_KEYS, start=1):
            self.menu.add.button(
                T.translate(key), lambda m=index: self._pick_month(m)
            )

    def _pick_month(self, month: int) -> None:
        self.selected_month = month
        self._build_day_menu()

    def _build_day_menu(self) -> None:
        self.menu.clear()
        self.menu.set_title(T.translate("select_day"))

        if self.selected_month in [4, 6, 9, 11]:
            max_days = 30
        elif self.selected_month == 2:
            max_days = 29
        else:
            max_days = 31

        for day in range(1, max_days + 1):
            self.menu.add.button(
                str(day), lambda d=day: self._pick_day(d), align=ALIGN_CENTER
            )

        self.menu.add.button(
            T.translate("select_month"), self._build_month_menu
        )

    def _pick_day(self, day: int) -> None:
        assert self.selected_month is not None
        self.callback((self.selected_month, day))
        self.client.pop_state()
