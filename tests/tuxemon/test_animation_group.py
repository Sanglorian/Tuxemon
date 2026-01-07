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
