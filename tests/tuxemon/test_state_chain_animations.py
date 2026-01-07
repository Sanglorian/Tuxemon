# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import logging
from unittest.mock import Mock, patch

import pytest

from tuxemon.animation import ScheduleType
from tuxemon.session import local_session
from tuxemon.state.state import State


@pytest.fixture
def fake_state():
    with patch.object(local_session, "_client", Mock()):
        state = State()
        state.task = Mock()
        return state


def test_chain_animations_calls_factories_in_order(fake_state):
    anim1 = Mock()
    anim2 = Mock()
    anim3 = Mock()
    f1 = Mock(return_value=anim1)
    f2 = Mock(return_value=anim2)
    f3 = Mock(return_value=anim3)
    fake_state.chain_animations(f1, f2, f3, start_delay=0)
    scheduled_func = fake_state.task.call_args[0][0]
    scheduled_func()  # calls f1
    anim1.schedule.call_args[0][0]()
    anim2.schedule.call_args[0][0]()
    f1.assert_called_once()
    f2.assert_called_once()
    f3.assert_called_once()
    anim1.schedule.assert_called_once()
    anim2.schedule.assert_called_once()
    anim3.schedule.assert_called_once()
    assert anim3.schedule.call_args.kwargs["when"] == ScheduleType.ON_FINISH
    assert anim1.schedule.call_args.kwargs["when"] == ScheduleType.ON_FINISH
    assert anim2.schedule.call_args.kwargs["when"] == ScheduleType.ON_FINISH


def test_chain_animations_passes_start_delay(fake_state):
    fake_state.chain_animations(lambda: Mock(), start_delay=250)
    fake_state.task.assert_called_once()
    assert fake_state.task.call_args.kwargs["interval"] == 250


def test_chain_animations_empty(fake_state):
    fake_state.chain_animations()
    fake_state.task.assert_called_once()
    scheduled_func = fake_state.task.call_args[0][0]
    scheduled_func()


def test_chain_animations_only_starts_first(fake_state):
    anim1 = Mock()
    anim2 = Mock()
    f1 = Mock(return_value=anim1)
    f2 = Mock(return_value=anim2)
    fake_state.chain_animations(f1, f2)
    scheduled_func = fake_state.task.call_args[0][0]
    f1.assert_not_called()
    f2.assert_not_called()
    scheduled_func()
    f1.assert_called_once()
    f2.assert_not_called()


def test_chain_animations_schedule_callback_is_callable(fake_state):
    anim = Mock()
    f = Mock(return_value=anim)
    fake_state.chain_animations(f)
    scheduled_func = fake_state.task.call_args[0][0]
    scheduled_func()
    callback = anim.schedule.call_args[0][0]
    assert callable(callback)


def test_chain_animations_no_errors_logged(fake_state, caplog):
    with caplog.at_level(logging.ERROR):
        fake_state.chain_animations(lambda: Mock())
        scheduled_func = fake_state.task.call_args[0][0]
        scheduled_func()
    assert caplog.text == ""
