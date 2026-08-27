# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.platform.const import buttons
from tuxemon.states.dialog_state import DialogState


def make_dialog(*, is_open):
    """A DialogState with only the attributes process_event touches.

    Building a real one needs a client, config and a display surface; the
    guard under test is independent of all of that.
    """
    state = object.__new__(DialogState)
    state._is_open = is_open
    state.advance_buttons = [buttons.A]
    state.text_queue = ["first line", "second line"]
    state.auto_close = True
    state.dialog_box = MagicMock(drawing_text=False)
    # DialogState.dialog is a read-only property onto the client
    state.client = MagicMock()
    state.client.alert_manager.is_dialog_complete.return_value = True
    state.client.alert_manager.is_busy.return_value = False
    state.next_text = MagicMock()
    return state


def press(button=buttons.A):
    return MagicMock(pressed=True, button=button)


def test_press_during_open_animation_is_ignored():
    """PopUpMenu runs on_open() only after a 0.2s animation.

    A press inside that window used to pop the first line off the queue
    before the box existed; on_open() then repainted over it, so the
    conversation appeared to restart with a blank first page.
    """
    state = make_dialog(is_open=False)

    assert state.process_event(press()) is None
    state.next_text.assert_not_called()
    assert state.text_queue == ["first line", "second line"]


def test_press_after_open_advances():
    state = make_dialog(is_open=True)

    assert state.process_event(press()) is None
    state.next_text.assert_called_once()


def test_press_during_open_animation_does_not_leak_to_the_world():
    """The press must still be consumed, or it re-triggers the map event."""
    state = make_dialog(is_open=False)

    assert state.process_event(press()) is None


@pytest.mark.parametrize(
    "drawing_text",
    [
        pytest.param(True, id="mid_typewriter"),
        pytest.param(False, id="line_complete"),
    ],
)
def test_guard_applies_regardless_of_box_state(drawing_text):
    state = make_dialog(is_open=False)
    state.dialog_box.drawing_text = drawing_text
    state.dialog.is_dialog_complete.return_value = not drawing_text

    state.process_event(press())

    state.dialog.dump_remaining_text.assert_not_called()
    state.next_text.assert_not_called()
