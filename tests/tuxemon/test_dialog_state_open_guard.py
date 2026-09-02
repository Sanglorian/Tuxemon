# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.menu.controller import MenuController
from tuxemon.platform.const import buttons
from tuxemon.states.dialog_state import DialogState


def controller_in(phase):
    """A real MenuController driven through its real transitions.

    Menu.resume opens the controller, then schedules set_normal() and
    on_open() together for the end of the open animation, so OPENING is
    exactly the window in which the box exists but holds no text yet.
    """
    controller = MenuController()
    if phase == "closed":
        return controller
    controller.open()  # CLOSED -> OPENING
    if phase == "opening":
        return controller
    controller.set_normal()  # OPENING -> NORMAL
    if phase == "normal":
        return controller
    if phase == "disabled":
        controller.disable()
        return controller
    if phase == "closing":
        controller.close()  # NORMAL -> CLOSING
        return controller
    raise ValueError(phase)


def make_dialog(*, is_open=None, phase=None):
    """A DialogState with only the attributes process_event touches.

    Building a real one needs a client, config and a display surface; the
    guard under test is independent of all of that.
    """
    if phase is None:
        phase = "normal" if is_open else "opening"
    state = object.__new__(DialogState)
    state.state_controller = controller_in(phase)
    state._advance_guard = 0.0
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


@pytest.mark.parametrize(
    "phase, advances",
    [
        pytest.param("closed", False, id="closed_swallows"),
        pytest.param("opening", False, id="opening_swallows"),
        pytest.param("normal", True, id="normal_advances"),
        pytest.param("disabled", False, id="disabled_swallows"),
        pytest.param("closing", False, id="closing_swallows"),
    ],
)
def test_guard_follows_the_real_menu_state_machine(phase, advances):
    """Only NORMAL is fully open; every other phase must swallow input."""
    state = make_dialog(phase=phase)

    assert state.process_event(press()) is None
    assert state.next_text.called is advances


FRAME = 1.0 / 60.0


def make_typing_dialog():
    """An open dialog part-way through drawing a line."""
    state = make_dialog(phase="normal")
    state.dialog_box.drawing_text = True
    state._was_drawing = True
    state.client.alert_manager.is_dialog_complete.return_value = False
    state._advance_guard = 0.0
    return state


def finish_line(state):
    """The line stops drawing, as a dump or the typewriter running out."""
    state.dialog_box.drawing_text = False
    state.client.alert_manager.is_dialog_complete.return_value = True


def run_guard_down(state):
    for _ in range(int(DialogState.ADVANCE_GUARD / FRAME) + 1):
        state._update_advance_guard(FRAME)


def test_fast_forwarding_is_never_held_off():
    """Pressing while text is drawing must dump it straight away."""
    state = make_typing_dialog()

    state.process_event(press())

    state.client.alert_manager.dump_remaining_text.assert_called_once()


def test_an_armed_guard_never_blocks_fast_forwarding():
    """The guard belongs on advancing only."""
    state = make_typing_dialog()
    state._arm_advance_guard()

    state.process_event(press())

    state.client.alert_manager.dump_remaining_text.assert_called_once()


def test_a_dumped_line_cannot_be_advanced_past_immediately():
    state = make_typing_dialog()

    state.process_event(press())  # fast-forwards
    finish_line(state)
    state._update_advance_guard(FRAME)  # the frame that sees it finish

    state.process_event(press())
    state.next_text.assert_not_called()


def test_a_line_that_typed_out_on_its_own_is_protected_too():
    """The guard follows the text, not the press.

    A line nobody fast-forwarded still must not be left the instant its
    last character lands.
    """
    state = make_typing_dialog()

    finish_line(state)  # typewriter ran out by itself
    state._update_advance_guard(FRAME)

    state.process_event(press())
    state.next_text.assert_not_called()

    run_guard_down(state)
    state.process_event(press())
    state.next_text.assert_called_once()


def test_the_advance_guard_expires():
    state = make_typing_dialog()
    state.process_event(press())
    finish_line(state)
    state._update_advance_guard(FRAME)

    run_guard_down(state)
    state.process_event(press())

    state.next_text.assert_called_once()


def test_a_line_still_drawing_never_arms_the_guard():
    state = make_typing_dialog()

    for _ in range(30):
        state._update_advance_guard(FRAME)

    assert state._advance_guard == 0.0


def test_mashing_cannot_blow_through_a_line():
    """The complaint: press twice and the line displays and is gone."""
    state = make_typing_dialog()

    frames_to_dump = None
    frames_to_advance = None
    for frame in range(600):
        state.process_event(press())
        if (
            frames_to_dump is None
            and state.client.alert_manager.dump_remaining_text.called
        ):
            frames_to_dump = frame
            finish_line(state)
        if state.next_text.called:
            frames_to_advance = frame
            break
        state._update_advance_guard(FRAME)

    guard_frames = DialogState.ADVANCE_GUARD / FRAME
    assert frames_to_dump == 0, "fast-forward should not be held off"
    assert frames_to_advance is not None, "line was never advanced past"
    assert frames_to_advance >= guard_frames - 1


def test_several_input_events_in_one_frame_cannot_skip_a_line():
    """Input arrives per event, but the guard only ticks once per frame.

    A press that dumps a line has to hold off the very next press even if
    that press lands in the same frame, before any update has run. Whether
    two events share a frame depends on how fast the player mashes against
    the frame rate, which makes the leak intermittent.
    """
    state = make_typing_dialog()

    state.process_event(press())  # fast-forwards, completing the line
    finish_line(state)
    state.process_event(press())  # same frame: no _update_advance_guard yet

    state.next_text.assert_not_called()
