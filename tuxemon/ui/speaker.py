# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tuxemon.entity.npc import NPC
    from tuxemon.locale.locale import TranslatorManager
    from tuxemon.session import Session

logger = logging.getLogger(__name__)

SPEAKER_PREFIX_MSGID = "dialogue_speaker_prefix"
DEFAULT_SPEAKER_PREFIX = "{name}: "
NAME_PLACEHOLDER = "{name}"
SPEAKER_CONTEXT_KEY = "dialogue_speaker"


def get_speaker_prefix(
    session: Session, character: NPC, translator: TranslatorManager
) -> str:
    """
    Return the prefix announcing that ``character`` is speaking.

    A character is only announced when they take over the conversation: the
    first line of an exchange is prefixed, the lines that follow are not,
    and the prefix comes back when a different character starts talking.
    Speaker-less dialogue (eg ``translated_dialog``, signs) leaves the
    current speaker untouched.

    The exchange is the map event being processed, so a chain of dialogue
    actions belonging to the same event counts as one conversation. Outside
    of an event there is nothing to chain to, and every line is prefixed.

    Parameters:
        session: Object containing the session information.
        character: The character speaking this line.
        translator: Translator used to look up the prefix template.

    Returns:
        The prefix to prepend to the dialogue, or an empty string when the
        character is already the one speaking.
    """
    if not session.client.config.dialog_speaker_names:
        return ""

    context = session.current_event_context
    if context is not None:
        if context.get(SPEAKER_CONTEXT_KEY) == character.slug:
            return ""
        context[SPEAKER_CONTEXT_KEY] = character.slug

    return format_speaker_prefix(character.name, translator)


def format_speaker_prefix(name: str, translator: TranslatorManager) -> str:
    """
    Build the prefix that announces who is speaking, eg "Maple: ".

    The template comes from the ``dialogue_speaker_prefix`` msgid so locales
    can pick their own punctuation and spacing. If the msgid is missing, or
    does not contain the ``{name}`` placeholder, the default template is used.

    Parameters:
        name: Display name of the speaking character, already localized.
        translator: Translator used to look up the prefix template.

    Returns:
        The prefix to prepend to the dialogue, or an empty string if there
        is no name to announce.
    """
    if not name:
        return ""

    template = translator.translate(SPEAKER_PREFIX_MSGID)

    if template == SPEAKER_PREFIX_MSGID:
        template = DEFAULT_SPEAKER_PREFIX
    elif NAME_PLACEHOLDER not in template:
        logger.warning(
            f"'{SPEAKER_PREFIX_MSGID}' is missing the '{NAME_PLACEHOLDER}' "
            f"placeholder: '{template}'. Using the default prefix instead."
        )
        template = DEFAULT_SPEAKER_PREFIX

    return template.replace(NAME_PLACEHOLDER, name)
