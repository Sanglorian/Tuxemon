# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.ui.speaker import (
    SPEAKER_CONTEXT_KEY,
    SPEAKER_PREFIX_MSGID,
    format_speaker_prefix,
    get_speaker_prefix,
)
from tuxemon.ui.text_formatter import TextFormatter


def make_translator(prefix_template=SPEAKER_PREFIX_MSGID):
    """A translator that only knows how to translate the prefix msgid."""
    translator = MagicMock()
    translator.translate.side_effect = lambda msgid: (
        prefix_template if msgid == SPEAKER_PREFIX_MSGID else msgid
    )
    return translator


def make_character(slug, name):
    character = MagicMock()
    character.slug = slug
    character.name = name
    return character


@pytest.fixture
def session():
    session = MagicMock()
    session.client.config.dialog_speaker_names = True
    session.current_event_context = None
    session.player.monsters = []
    session.player.game_variables = {}
    return session


def test_format_speaker_prefix_defaults_when_untranslated():
    prefix = format_speaker_prefix("Maple", make_translator())
    assert prefix == "Maple: "


def test_format_speaker_prefix_uses_locale_template():
    translator = make_translator("<{name}> ")
    assert format_speaker_prefix("Maple", translator) == "<Maple> "


def test_format_speaker_prefix_falls_back_without_placeholder():
    translator = make_translator("nonsense")
    assert format_speaker_prefix("Maple", translator) == "Maple: "


def test_format_speaker_prefix_without_name():
    assert format_speaker_prefix("", make_translator()) == ""


def test_get_speaker_prefix_names_the_first_line(session):
    maple = make_character("npc_maple", "Maple")
    prefix = get_speaker_prefix(session, maple, make_translator())
    assert prefix == "Maple: "


def test_get_speaker_prefix_disabled_by_config(session):
    session.client.config.dialog_speaker_names = False
    maple = make_character("npc_maple", "Maple")
    assert get_speaker_prefix(session, maple, make_translator()) == ""


def test_get_speaker_prefix_skips_the_rest_of_the_exchange(session):
    session.current_event_context = {}
    maple = make_character("npc_maple", "Maple")
    translator = make_translator()

    assert get_speaker_prefix(session, maple, translator) == "Maple: "
    assert get_speaker_prefix(session, maple, translator) == ""
    assert session.current_event_context[SPEAKER_CONTEXT_KEY] == "npc_maple"


def test_get_speaker_prefix_returns_when_the_speaker_changes(session):
    session.current_event_context = {}
    maple = make_character("npc_maple", "Maple")
    cleo = make_character("npc_cleo", "Cleo")
    translator = make_translator()

    assert get_speaker_prefix(session, maple, translator) == "Maple: "
    assert get_speaker_prefix(session, cleo, translator) == "Cleo: "
    assert get_speaker_prefix(session, maple, translator) == "Maple: "


def test_get_speaker_prefix_outside_an_event(session):
    """Without an exchange to chain to, every line is named."""
    maple = make_character("npc_maple", "Maple")
    translator = make_translator()

    assert get_speaker_prefix(session, maple, translator) == "Maple: "
    assert get_speaker_prefix(session, maple, translator) == "Maple: "


def test_prefix_only_lands_on_the_first_page(session):
    translator = MagicMock()
    translator.format.return_value = "Hello there.\nHow are you?"

    pages = TextFormatter(session, translator).paginate_translation(
        "greeting", prefix="Maple: "
    )

    assert list(pages) == ["Maple: Hello there.", "How are you?"]


def test_pagination_without_a_prefix(session):
    translator = MagicMock()
    translator.format.return_value = "Hello there.\nHow are you?"

    pages = TextFormatter(session, translator).paginate_translation("greeting")

    assert list(pages) == ["Hello there.", "How are you?"]
