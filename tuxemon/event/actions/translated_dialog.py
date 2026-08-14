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
class TranslatedDialogAction(EventAction):
    """
    Open a dialog window with translated text according to the passed
    translation key. Parameters passed to the translation string will also
    be checked if a translation key exists.

    Naming a speaker introduces the line with that character's name, eg
    "Maple: Hello there!". The name is added before the text is paginated, so
    it only appears on the first page. It is announced when a character takes
    over the conversation: the first line of an exchange is named, the lines
    that follow are not, and the name comes back when a different character
    starts talking. An exchange is the map event being run, so every dialog
    action of the same event belongs to one conversation, and the speaker can
    safely be named on every line of it.

    Script usage:
        .. code-block::

            translated_dialog <text>[,avatar][,position][,style][,speaker]

    Script parameters:
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
        style: a predefined style in db/dialogue/dialogue.json
        speaker: Character saying the line, either "player" or the slug of an
            NPC (e.g. "npc_maple"). Their name introduces the dialog. Being
            the last parameter, it is usually passed by name.

    Example:
        translated_dialog junkyard_01,speaker=npc_maple
    """

    name = "translated_dialog"
    raw_parameters: str
    avatar: str | None = None
    position: str | None = None
    h_alignment: str | None = None
    v_alignment: str | None = None
    style: str | None = None
    speaker: str | None = None

    def start(self, session: Session) -> None:
        key = TextFormatter(session, T).paginate_translation(
            self.raw_parameters, prefix=self._get_prefix(session)
        )
        if key == self.raw_parameters:
            logger.warning(
                f"No translation found for key: {self.raw_parameters}"
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

    def _get_prefix(self, session: Session) -> str:
        """Return the name introducing the speaker, if there is one."""
        if self.speaker is None:
            return ""

        character = session.client.get_npc(self.speaker)
        if character is None:
            logger.error(f"{self.speaker} not found, dialog left unnamed")
            return ""

        return get_speaker_prefix(session, character, T)

    def update(self, session: Session, dt: float) -> None:
        if "DialogState" not in session.client.active_state_names:
            self.stop()
