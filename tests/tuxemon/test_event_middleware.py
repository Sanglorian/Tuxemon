# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pytest

from tuxemon.event.eventmiddleware import (
    ButtonFilterMiddleware,
    EventMiddleware,
    InputTranslatorMiddleware,
    IntentionFilterMiddleware,
)
from tuxemon.platform.const import buttons, events, intentions
from tuxemon.platform.events import PlayerInput


class DummyMiddleware(EventMiddleware):
    def preprocess(self, event: PlayerInput):
        return event

    def postprocess(self, processed_event: PlayerInput):
        return processed_event


def test_cannot_instantiate_abstract():
    with pytest.raises(TypeError):
        EventMiddleware()


def test_subclass_must_implement_methods():
    mw = DummyMiddleware()
    event = PlayerInput(button="TEST", value=1, hold_time=0)
    assert mw.preprocess(event) is event
    assert mw.postprocess(event) is event


@pytest.mark.parametrize(
    "preprocess_return, postprocess_return, expected_pre, expected_post",
    [
        (None, "event", None, "event"),  # preprocess consumes
        ("event", None, "event", None),  # postprocess consumes
    ],
)
def test_consuming_middleware(
    preprocess_return, postprocess_return, expected_pre, expected_post
):
    class ConsumingMiddleware(EventMiddleware):
        def preprocess(self, event: PlayerInput):
            return preprocess_return if preprocess_return != "event" else event

        def postprocess(self, processed_event: PlayerInput):
            return (
                postprocess_return
                if postprocess_return != "event"
                else processed_event
            )

    mw = ConsumingMiddleware()
    event = PlayerInput(button="TEST", value=1, hold_time=0)

    pre = mw.preprocess(event)
    post = mw.postprocess(event)

    assert (pre is None) if expected_pre is None else (pre is event)
    assert (post is None) if expected_post is None else (post is event)


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


@pytest.fixture
def button_filter():
    return ButtonFilterMiddleware()


def test_event_passes_through_if_not_blocked(button_filter):
    event = PlayerInput(button=buttons.UP, value=1, hold_time=0)
    assert button_filter.preprocess(event) is event


def test_event_blocked_if_in_blocklist(button_filter):
    button_filter.block_button(buttons.UP)
    event = PlayerInput(button=buttons.UP, value=1, hold_time=0)
    assert button_filter.preprocess(event) is None


def test_unblock_button_allows_event(button_filter):
    button_filter.block_button(buttons.UP)
    button_filter.unblock_button(buttons.UP)
    event = PlayerInput(button=buttons.UP, value=1, hold_time=0)
    assert button_filter.preprocess(event) is event


def test_initially_blocked_buttons_constructor():
    mw = ButtonFilterMiddleware(initially_blocked_buttons={buttons.DOWN})
    event = PlayerInput(button=buttons.DOWN, value=1, hold_time=0)
    assert mw.preprocess(event) is None


def test_postprocess_returns_event(button_filter):
    event = PlayerInput(button=buttons.LEFT, value=1, hold_time=0)
    assert button_filter.postprocess(event) is event


def test_postprocess_none(button_filter):
    assert button_filter.postprocess(None) is None


@pytest.fixture
def intention_filter():
    return IntentionFilterMiddleware()


def test_global_block_consumes_event(intention_filter):
    event = PlayerInput(button=intentions.UP, value=1, hold_time=0)
    assert intention_filter.preprocess(event) is None


def test_allow_specific_action(intention_filter):
    intention_filter.update_allowed_actions({intentions.UP})
    event = PlayerInput(button=intentions.UP, value=1, hold_time=0)
    assert intention_filter.preprocess(event) is event


def test_block_unlisted_action(intention_filter):
    intention_filter.update_allowed_actions({intentions.UP})
    event = PlayerInput(button=intentions.DOWN, value=1, hold_time=0)
    assert intention_filter.preprocess(event) is None


def test_open_gate_allows_everything(intention_filter):
    intention_filter.update_allowed_actions(
        IntentionFilterMiddleware.OPEN_GATE
    )
    event1 = PlayerInput(button=intentions.UP, value=1, hold_time=0)
    event2 = PlayerInput(button=intentions.DOWN, value=1, hold_time=0)
    assert intention_filter.preprocess(event1) is event1
    assert intention_filter.preprocess(event2) is event2


def test_postprocess_returns_event(intention_filter):
    event = PlayerInput(button=intentions.LEFT, value=1, hold_time=0)
    assert intention_filter.postprocess(event) is event


def test_postprocess_none(intention_filter):
    assert intention_filter.postprocess(None) is None
