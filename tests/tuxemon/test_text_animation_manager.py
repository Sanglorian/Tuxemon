# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.ui.combat_notifier import TextAnimationManager


@pytest.fixture
def manager():
    return TextAnimationManager()


def test_add_text_animation_queues_items(manager):
    fn = MagicMock()
    manager.add_text_animation(fn, 1.5)
    assert len(manager.text_queue) == 1
    anim, duration = manager.text_queue[0]
    assert duration == 1.5


def test_update_text_animation_triggers_when_time_runs_out(manager):
    fn = MagicMock()
    manager.add_text_animation(fn, 1.0)
    manager.update_text_animation(1.1)
    fn.assert_called_once()
    assert len(manager.text_queue) == 0
    assert manager._text_time_left == 1.0


def test_update_text_animation_does_not_trigger_too_early(manager):
    fn = MagicMock()
    manager.add_text_animation(fn, 2.0)
    manager.update_text_animation(1.0)
    fn.assert_called_once()


def test_multiple_animations_trigger_in_order(manager):
    fn1 = MagicMock()
    fn2 = MagicMock()
    manager.add_text_animation(fn1, 1.0)
    manager.add_text_animation(fn2, 2.0)
    manager.update_text_animation(1.1)
    fn1.assert_called_once()
    fn2.assert_not_called()
    manager.update_text_animation(2.1)
    fn2.assert_called_once()


def test_xp_messages_are_batched(manager):
    manager.add_xp_message("XP +10")
    manager.add_xp_message("XP +20")
    alert = MagicMock()
    text_area = MagicMock()
    manager.trigger_xp_animation(alert, text_area)
    assert len(manager.text_queue) == 1
    anim, duration = manager.text_queue[0]
    anim()
    alert.assert_called_once_with("XP +10\nXP +20", text_area)
    assert manager._xp_messages == []
    assert manager._pending_xp_duration == duration


def test_zero_duration_triggers_immediately(manager):
    fn = MagicMock()
    manager.add_text_animation(fn, 0)
    manager.update_text_animation(0.01)
    fn.assert_called_once()


def test_multiple_zero_duration_animations(manager):
    fn1 = MagicMock()
    fn2 = MagicMock()
    fn3 = MagicMock()
    manager.add_text_animation(fn1, 0)
    manager.add_text_animation(fn2, 0)
    manager.add_text_animation(fn3, 0)
    manager.update_text_animation(0.01)
    fn1.assert_called_once()
    fn2.assert_not_called()
    fn3.assert_not_called()
    manager.update_text_animation(0.01)
    fn2.assert_called_once()
    manager.update_text_animation(0.01)
    fn3.assert_called_once()


def test_time_left_set_to_duration_of_popped_animation(manager):
    fn = MagicMock()
    manager.add_text_animation(fn, 3.5)
    manager.update_text_animation(0.01)
    assert manager._text_time_left == 3.5


def test_trigger_xp_animation_sets_pending_duration(manager):
    manager.add_xp_message("XP +10")
    manager.add_xp_message("XP +20")
    alert = MagicMock()
    text_area = MagicMock()
    manager.trigger_xp_animation(alert, text_area)
    assert manager._xp_messages == []
    assert manager._pending_xp_duration is not None


def test_xp_animation_calls_alert(manager):
    manager.add_xp_message("XP +10")
    alert = MagicMock()
    text_area = MagicMock()
    manager.trigger_xp_animation(alert, text_area)
    anim, duration = manager.text_queue[0]
    anim()
    alert.assert_called_once_with("XP +10", text_area)
