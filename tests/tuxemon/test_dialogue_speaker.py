# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest
from pygame.rect import Rect

from tuxemon.database.runtime import db
from tuxemon.db import ParameterizableRule
from tuxemon.event.actions.translated_dialog import style_cache
from tuxemon.event.eventaction import ActionManager
from tuxemon.event.running import RunningEvent
from tuxemon.ui.dialogue import calc_dialog_rect
from tuxemon.ui.text_alignment import DialogPosition


@pytest.fixture(scope="module", autouse=True)
def dialogue_styles():
    """The dialog action looks up its box style in the database."""
    db.load("dialogue", validate=False)
    style_cache.preload(["default"])


def make_character(slug, name):
    character = MagicMock()
    character.slug = slug
    character.name = name
    return character


@pytest.fixture
def characters():
    return {
        "npc_maple": make_character("npc_maple", "Maple"),
        "npc_cleo": make_character("npc_cleo", "Cleo"),
    }


@pytest.fixture
def session(characters):
    session = MagicMock()
    session.current_event_context = None
    session.client.get_npc.side_effect = characters.get
    session.client.config.dialog_speaker_names = True
    session.client.config.dialog_box_style = "default"
    session.client.context.rect = Rect(0, 0, 800, 600)
    # no DialogState is ever pushed, so every dialog action ends immediately
    session.client.active_state_names = []
    session.player.name = "Jeff"
    session.player.monsters = []
    session.player.game_variables = {}
    return session


def run_event(session, *actions):
    """Run a chain of actions as a single map event, return the dialog pages."""
    map_event = MagicMock()
    map_event.delay = None
    map_event.timeout = None
    rules = [
        ParameterizableRule(type=action[0], parameters=list(action[1:]))
        for action in actions
    ]
    event = RunningEvent(map_event, rules)
    event.running()
    event.process(session, ActionManager(), 0.0)

    return [
        call.kwargs["text"]
        for call in session.client.push_state.call_args_list
        if call.args and call.args[0] == "DialogState"
    ]


def test_speaker_is_named_once_per_exchange(session):
    pages = run_event(
        session,
        ("translated_dialog", "unit_test_line_1", "speaker=npc_maple"),
        ("translated_dialog", "unit_test_line_2", "speaker=npc_maple"),
    )

    assert pages == [["Maple: unit_test_line_1"], ["unit_test_line_2"]]


def test_speaker_is_named_again_when_it_changes(session):
    pages = run_event(
        session,
        ("translated_dialog", "unit_test_line_1", "speaker=npc_maple"),
        ("translated_dialog", "unit_test_line_2", "speaker=npc_cleo"),
        ("translated_dialog", "unit_test_line_3", "speaker=npc_maple"),
    )

    assert pages == [
        ["Maple: unit_test_line_1"],
        ["Cleo: unit_test_line_2"],
        ["Maple: unit_test_line_3"],
    ]


def test_speakerless_dialog_does_not_break_the_exchange(session):
    pages = run_event(
        session,
        ("translated_dialog", "unit_test_line_1", "speaker=npc_maple"),
        ("translated_dialog", "unit_test_line_2"),
        ("translated_dialog", "unit_test_line_3", "speaker=npc_maple"),
    )

    assert pages == [
        ["Maple: unit_test_line_1"],
        ["unit_test_line_2"],
        ["unit_test_line_3"],
    ]


def test_separate_events_are_separate_exchanges(session):
    first = run_event(
        session, ("translated_dialog", "unit_test_line_1", "speaker=npc_maple")
    )
    session.client.push_state.reset_mock()
    second = run_event(
        session, ("translated_dialog", "unit_test_line_2", "speaker=npc_maple")
    )

    assert first == [["Maple: unit_test_line_1"]]
    assert second == [["Maple: unit_test_line_2"]]


def test_unknown_character_still_shows_the_dialog(session):
    pages = run_event(
        session,
        ("translated_dialog", "unit_test_line_1", "speaker=npc_nobody"),
    )

    assert pages == [["unit_test_line_1"]]


def test_names_can_be_turned_off(session):
    session.client.config.dialog_speaker_names = False

    pages = run_event(
        session, ("translated_dialog", "unit_test_line_1", "speaker=npc_maple")
    )

    assert pages == [["unit_test_line_1"]]


def test_event_context_is_released_after_processing(session):
    run_event(
        session, ("translated_dialog", "unit_test_line_1", "speaker=npc_maple")
    )

    assert session.current_event_context is None


def test_speaker_can_be_passed_positionally(session):
    """It is the last parameter, so the ones before it have to be empty."""
    pages = run_event(
        session,
        (
            "translated_dialog",
            "unit_test_line_1",
            "",
            "",
            "",
            "",
            "",
            "npc_maple",
        ),
    )

    assert pages == [["Maple: unit_test_line_1"]]


def test_a_named_parameter_leaves_the_others_alone(session):
    """Naming the speaker must not shift the positional parameters."""
    pages = run_event(
        session,
        (
            "translated_dialog",
            "unit_test_line_1",
            "",
            "center",
            "speaker=npc_maple",
        ),
    )

    rect = session.client.push_state.call_args_list[0].kwargs["rect"]
    assert pages == [["Maple: unit_test_line_1"]]
    assert rect == calc_dialog_rect(
        session.client.context.rect, DialogPosition.CENTER
    )


@pytest.fixture
def dialogue_profile(monkeypatch):
    """Give char_talk a profile that answers with the field it was asked for."""
    manager = MagicMock()
    manager.get_dialogue_line.side_effect = lambda content, field: field
    monkeypatch.setattr(
        "tuxemon.event.actions.char_talk.DialogueProfileManager",
        lambda: manager,
    )
    return manager


def test_char_talk_names_the_speaker(session, dialogue_profile):
    pages = run_event(session, ("char_talk", "npc_maple", "greeting"))

    assert pages == [["Maple: greeting"]]


def test_char_talk_shares_the_exchange_with_dialog(session, dialogue_profile):
    pages = run_event(
        session,
        ("translated_dialog", "unit_test_line_1", "speaker=npc_maple"),
        ("char_talk", "npc_maple", "farewell"),
        ("char_talk", "npc_cleo", "greeting"),
    )

    assert pages == [
        ["Maple: unit_test_line_1"],
        ["farewell"],
        ["Cleo: greeting"],
    ]
