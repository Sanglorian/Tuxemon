# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import logging
from unittest.mock import Mock

import pytest

from tuxemon.animation import Animation, ScheduleType, Task
from tuxemon.state.animation_group import AnimationGroup


@pytest.fixture
def group():
    return AnimationGroup()


@pytest.fixture
def fake_group():
    group = AnimationGroup()
    group.task = Mock()
    return group


@pytest.fixture
def dummy_target():
    class Dummy:
        x = 0

    return Dummy()


@pytest.fixture
def dummy_callback():
    return Mock()


def test_animate_adds_animation_to_group(group, dummy_target):
    ani = group.animate(dummy_target, x=0)
    assert isinstance(ani, Animation)
    assert ani in group._group


@pytest.mark.parametrize(
    "kwargs",
    [
        {"x": 0},
        {"duration": 1.0, "x": 5},
        {"duration": 0.5, "opacity": 1},
    ],
)
def test_animate_parametrized(group, dummy_target, kwargs):
    ani = group.animate(dummy_target, **kwargs)
    assert ani in group._group


def test_task_creates_task(group, dummy_callback):
    task = group.task(dummy_callback)
    assert isinstance(task, Task)
    assert task in group._group


def test_task_requires_callable(group):
    with pytest.raises(ValueError):
        group.task("not-a-function")


def test_task_schedules_on_finish(group, dummy_callback):
    finish = Mock()
    task = group.task(dummy_callback, on_finish=finish)
    assert ScheduleType.ON_FINISH in task._callbacks


def test_task_invalid_schedule_type_raises(group, dummy_callback):
    with pytest.raises(ValueError):
        group.task(dummy_callback, not_a_real_trigger=lambda: None)


@pytest.mark.parametrize(
    "schedule_type",
    [
        "on finish",
        "on interval",
    ],
)
def test_task_parametrized_schedule_types(
    group, dummy_callback, schedule_type
):
    cb = Mock()
    task = group.task(dummy_callback, **{schedule_type: cb})
    assert ScheduleType(schedule_type) in task._callbacks


def test_update_calls_update_on_group(group, dummy_callback):
    task = group.task(dummy_callback)
    task.update = Mock()
    group.update(0.1)
    task.update.assert_called_once()


def test_clear_aborts_tasks(group, dummy_callback):
    task = group.task(dummy_callback)
    task.abort = Mock()
    group.clear()
    task.abort.assert_called_once()
    assert len(group._group) == 0


def test_clear_handles_empty_group(group):
    group.clear()
    assert len(group._group) == 0


def test_remove_of_removes_matching_animations(group, dummy_target):
    ani = group.animate(dummy_target, x=0)
    assert ani in group._group
    group.remove_of(dummy_target)
    assert ani not in group._group


def test_remove_of_does_not_remove_unrelated(group, dummy_target):
    ani1 = group.animate(dummy_target, x=0)

    class Dummy2:
        x = 0

    ani2 = group.animate(Dummy2(), x=0)
    group.remove_of(dummy_target)
    assert ani1 not in group._group
    assert ani2 in group._group


def test_remove_of_no_matches_logs_debug(group, caplog):
    with caplog.at_level(logging.DEBUG):
        group.remove_of(object())
    assert "No animations found" in caplog.text


def test_chain_animations_calls_factories_in_order(fake_group):
    anim1 = Mock()
    anim2 = Mock()
    anim3 = Mock()
    f1 = Mock(return_value=anim1)
    f2 = Mock(return_value=anim2)
    f3 = Mock(return_value=anim3)
    fake_group.chain_animations(f1, f2, f3, start_delay=0)
    scheduled_func = fake_group.task.call_args[0][0]
    scheduled_func()
    anim1.schedule.call_args[0][0]()
    anim2.schedule.call_args[0][0]()
    f1.assert_called_once()
    f2.assert_called_once()
    f3.assert_called_once()
    anim1.schedule.assert_called_once()
    anim2.schedule.assert_called_once()
    anim3.schedule.assert_called_once()
    assert anim1.schedule.call_args.kwargs["when"] == ScheduleType.ON_FINISH
    assert anim2.schedule.call_args.kwargs["when"] == ScheduleType.ON_FINISH
    assert anim3.schedule.call_args.kwargs["when"] == ScheduleType.ON_FINISH


def test_chain_animations_passes_start_delay(fake_group):
    fake_group.chain_animations(lambda: Mock(), start_delay=250)
    fake_group.task.assert_called_once()
    assert fake_group.task.call_args.kwargs["interval"] == 250


def test_chain_animations_only_starts_first(fake_group):
    anim1 = Mock()
    anim2 = Mock()
    f1 = Mock(return_value=anim1)
    f2 = Mock(return_value=anim2)
    fake_group.chain_animations(f1, f2)
    scheduled_func = fake_group.task.call_args[0][0]
    f1.assert_not_called()
    f2.assert_not_called()
    scheduled_func()
    f1.assert_called_once()
    f2.assert_not_called()


def test_chain_animations_schedule_callback_is_callable(fake_group):
    anim = Mock()
    f = Mock(return_value=anim)
    fake_group.chain_animations(f)
    scheduled_func = fake_group.task.call_args[0][0]
    scheduled_func()
    callback = anim.schedule.call_args[0][0]
    assert callable(callback)


def test_chain_animations_no_errors_logged(fake_group, caplog):
    with caplog.at_level(logging.ERROR):
        fake_group.chain_animations(lambda: Mock())
        scheduled_func = fake_group.task.call_args[0][0]
        scheduled_func()
    assert caplog.text == ""
