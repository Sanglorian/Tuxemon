# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from tuxemon.graphics import load_and_scale
from tuxemon.menu.menu import PopUpMenu
from tuxemon.platform.const import buttons
from tuxemon.platform.events import PlayerInput
from tuxemon.sprite import Sprite
from tuxemon.tools import scale
from tuxemon.ui.text import TextArea
from tuxemon.ui.text_alignment import HorizontalAlignment, VerticalAlignment

if TYPE_CHECKING:
    from tuxemon.platform.events import PlayerInput
    from tuxemon.sprite import Sprite

logger = logging.getLogger(__name__)


class DialogState(PopUpMenu[None]):
    """
    Game state with a graphic box and some text in it.

    Pressing the action button:
    * if text is being displayed, will cause text speed to go max
    * when text is displayed completely, then will show the next message
    * if there are no more messages, then the dialog will close
    """

    name: ClassVar[str] = "DialogState"

    def __init__(
        self,
        text: Sequence[str] = (),
        avatar: Optional[Sprite] = None,
        box_style: Optional[dict[str, Any]] = None,
        on_complete: Optional[Callable[[], None]] = None,
        advance_buttons: Optional[list[int]] = None,
        timeout: Optional[float] = None,
        autoclose: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.text_queue = list(text)
        self.avatar = avatar
        self.on_complete = on_complete
        self.advance_buttons = advance_buttons or [buttons.A]

        # Auto-close settings
        self.timeout = timeout
        self.autoclose = autoclose
        self.elapsed = 0.0

        # Box style setup
        default_box_style: dict[str, Any] = {
            "bg_color": self.background_color,
            "font_color": self.font_color,
            "font_shadow": self.font_shadow_color,
            "border": self.borders_filename,
            "line_spacing": 0,
            "h_alignment": HorizontalAlignment.LEFT,
            "v_alignment": VerticalAlignment.TOP,
        }

        final_box_style = default_box_style.copy()
        box_style = box_style or {}
        final_box_style.update(box_style)

        _border = load_and_scale(final_box_style["border"])
        self.window._set_border(_border)
        self.window._color = final_box_style["bg_color"]
        line_spacing = scale(final_box_style["line_spacing"])

        self.dialog_box = TextArea(
            font=self.font,
            font_color=final_box_style["font_color"],
            font_shadow=final_box_style["font_shadow"],
            h_alignment=final_box_style["h_alignment"],
            v_alignment=final_box_style["v_alignment"],
            line_spacing=line_spacing,
        )
        self.dialog_box.rect = self.calc_internal_rect()
        self.sprites.add(self.dialog_box)

        if self.avatar:
            avatar_rect = self.calc_final_rect()
            self.avatar.rect.bottomleft = avatar_rect.left, avatar_rect.top
            self.sprites.add(self.avatar)

    def on_open(self) -> None:
        self.next_text()

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.timeout is not None:
            self.elapsed += dt
            if self.elapsed >= self.timeout:
                # Always finish current line, then advance
                if self.dialog_box.drawing_text:
                    self.dialog.dump_remaining_text(self.dialog_box)
                self.next_text()
                self.elapsed = 0.0

    def add_advance_button(self, button: int) -> None:
        if button not in self.advance_buttons:
            self.advance_buttons.append(button)

    def remove_advance_button(self, button: int) -> None:
        if button in self.advance_buttons:
            self.advance_buttons.remove(button)

    def process_event(self, event: PlayerInput) -> Optional[PlayerInput]:
        if event.pressed and event.button in self.advance_buttons:
            if not self.dialog.is_dialog_complete(self.dialog_box):
                logger.debug("Fast-forwarding current dialog line")
                self.dialog.dump_remaining_text(self.dialog_box)
            else:
                logger.debug("Dialog line complete, advancing to next")
                self.next_text()
        return None

    def next_text(self) -> Optional[str]:
        if self.dialog_box.drawing_text:
            return None

        try:
            text = self.text_queue.pop(0)
            self.dialog.alert(text)
            self.elapsed = 0.0
            return text
        except IndexError:
            if self.autoclose:
                self.client.pop_state(self)
                if self.on_complete:
                    self.on_complete()
            return None
