# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pytest

from tuxemon.event.eventmiddleware import InputTranslatorMiddleware
from tuxemon.platform.const import buttons, events, intentions
from tuxemon.platform.events import PlayerInput


@pytest.fixture
def translator():
    return InputTranslatorMiddleware()


@pytest.mark.parametrize(
    "button,value,expected_button",
    [
        (buttons.UP, 1, intentions.UP),
        (buttons.DOWN, 1, intentions.DOWN),
        ("UNKNOWN", 1, "UNKNOWN"),
        (events.UNICODE, "n", intentions.NOCLIP),
        (events.UNICODE, "x", events.UNICODE),
    ],
)
def test_translate_buttons(translator, button, value, expected_button):
    event = PlayerInput(button=button, value=value, hold_time=0)
    translated = translator.preprocess(event)
    assert translated.button == expected_button


def test_postprocess_returns_same_event(translator):
    event = PlayerInput(button=buttons.LEFT, value=1, hold_time=0)
    assert translator.postprocess(event) is event


def test_postprocess_none(translator):
    assert translator.postprocess(None) is None


def test_event_fields_preserved(translator):
    event = PlayerInput(
        button=buttons.RIGHT,
        value=42,
        hold_time=3.5,
        previous_value=99,
        timestamp=1234567890.0,
        hold_duration=2.0,
    )
    translated = translator.preprocess(event)
    assert translated.value == 42
    assert translated.hold_time == 3.5
    assert translated.previous_value == 99
    assert translated.timestamp == 1234567890.0
    assert translated.hold_duration == 2.0
