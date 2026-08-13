# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, final

from tuxemon.event.eventaction import EventAction
from tuxemon.graphics import string_to_colorlike
from tuxemon.locale.locale import T
from tuxemon.monster.avatar import get_avatar
from tuxemon.session import Session
from tuxemon.tools import open_dialog, safe_enum_value
from tuxemon.ui.dialogue import DialogueStyleCache
from tuxemon.ui.speaker import get_speaker_prefix
from tuxemon.ui.text_alignment import (
    DialogPosition,
    HorizontalAlignment,
    VerticalAlignment,
)
from tuxemon.ui.text_formatter import TextFormatter

logger = logging.getLogger(__name__)


style_cache = DialogueStyleCache()


@final
@dataclass
class CharDialogAction(EventAction):
    """
    Open a dialog window with translated text, introduced by the name of the
    character who is speaking (e.g. "Maple: Hello there!").

    This behaves exactly like ``translated_dialog``, except that it knows who
    is talking. The speaker's localized name is prepended to the text before
    it is paginated, so the name only ever appears on the first page.

    The name is announced when a character takes over the conversation: the
    first line of an exchange is named, the lines that follow are not, and the
    name comes back when a different character starts talking. An exchange is
    the map event being run, so every dialog action of the same event belongs
    to one conversation. This means it is safe to use for every line of a
    conversation, and it can be mixed freely with ``char_talk``.

    Script usage:
        .. code-block::

            char_dialog <character>,<text>[,avatar][,position][,h_alignment][,v_alignment][,style]

    Script parameters:
        character: Either "player" or the slug of an NPC (e.g. "npc_maple").
        text: Text of the dialog.
        avatar: Monster avatar. If it is a number, the monster is the
            corresponding monster slot in the player's party.
            If it is a string, we're referring to a monster by name.
        position: Position of the dialog box. Can be 'top', 'bottom', 'center',
            'topleft', 'topright', 'bottomleft', 'bottomright', 'right', 'left'.
            Default 'bottom'.
        h_alignment: Alignment of text in the dialog box, it can be 'left', 'center'
            or 'right'. Default 'left'.
        v_alignment: Alignment of text in the dialog box, it can be 'bottom',
            'center' or 'top'. Default 'top'.
        style: a predefined style in db/dialogue/dialogue.yaml

    Example:
        char_dialog npc_maple,junkyard_01
    """

    name = "char_dialog"
    character: str
    raw_parameters: str
    avatar: str | None = None
    position: str | None = None
    h_alignment: str | None = None
    v_alignment: str | None = None
    style: str | None = None

    def start(self, session: Session) -> None:
        character = session.client.get_npc(self.character)
        if character is None:
            logger.error(f"{self.character} not found, dialog left unnamed")
            prefix = ""
        else:
            prefix = get_speaker_prefix(session, character, T)

        key = TextFormatter(session, T).paginate_translation(
            self.raw_parameters, prefix=prefix
        )

        avatar_sprite = (
            get_avatar(session, self.avatar) if self.avatar else None
        )

        dialogue = self.style or session.client.config.dialog_box_style
        style = style_cache.get(dialogue)
        h_alignment = safe_enum_value(
            HorizontalAlignment, self.h_alignment, HorizontalAlignment.LEFT
        )
        v_alignment = safe_enum_value(
            VerticalAlignment, self.v_alignment, VerticalAlignment.TOP
        )
        box_style: dict[str, Any] = {
            "bg_color": string_to_colorlike(style.bg_color),
            "font_color": string_to_colorlike(style.font_color),
            "font_shadow": string_to_colorlike(style.font_shadow_color),
            "border": style.border_path,
            "line_spacing": style.line_spacing,
            "h_alignment": h_alignment,
            "v_alignment": v_alignment,
        }

        position = safe_enum_value(
            DialogPosition, self.position, DialogPosition.BOTTOM
        )
        open_dialog(
            client=session.client,
            text=key,
            avatar=avatar_sprite,
            box_style=box_style,
            position=position,
            target_coords=None,
            custom_rect=None,
        )

    def update(self, session: Session, dt: float) -> None:
        if "DialogState" not in session.client.active_state_names:
            self.stop()
