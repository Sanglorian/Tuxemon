# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock
from weakref import ref

from tuxemon.animation import Animation, AnimationState, ScheduleType


class TestAnimation(unittest.TestCase):
    def setUp(self) -> None:
        self.ani = Animation(x=100, y=100, duration=1000)
        self.sprite = MagicMock()

    def test_init(self):
        self.assertEqual(self.ani.props, {"x": 100, "y": 100})
        self.assertEqual(self.ani.delay, 0)
        self.assertEqual(self.ani._duration, 1000)
        self.assertEqual(self.ani._relative, False)

    def test_init_with_targets(self):
        ani = Animation(self.sprite, x=100, y=100, duration=1000)
        self.assertEqual(ani._targets, [ref(self.sprite)])

    def test_start(self):
        self.ani.start(self.sprite)
        self.assertEqual(self.ani._state, AnimationState.RUNNING)
        self.assertIsInstance(self.ani._targets[0], ref)
        self.assertEqual(self.ani._targets[0](), self.sprite)

    def test_start_multiple_times(self):
        self.ani.start(self.sprite)
        with self.assertRaises(RuntimeError):
            self.ani.start(self.sprite)

    def test_update(self):
        self.ani.start(self.sprite)
        self.ani.update(500)
        self.assertEqual(self.ani._elapsed, 500)

    def test_update_before_start(self):
        self.ani.update(500)
        self.assertEqual(self.ani._elapsed, 0)

    def test_finish(self):
        self.ani.start(self.sprite)
        self.ani.finish()
        self.assertEqual(self.ani._state, AnimationState.FINISHED)

    def test_abort(self):
        self.ani.start(self.sprite)
        self.ani.abort()
        self.assertEqual(self.ani._state, AnimationState.ABORTED)

    def test_get_value(self):
        self.sprite.x = 50
        self.assertEqual(self.ani._get_value(self.sprite, "x"), 50)

    def test_get_value_callable(self):
        self.sprite.x = lambda: 50
        self.assertEqual(self.ani._get_value(self.sprite, "x"), 50)

    def test_set_value(self):
        self.ani._set_value(self.sprite, "x", 100)
        self.sprite.x.assert_called_once_with(100)

    def test_set_value_callable(self):
        self.sprite.x = MagicMock()
        self.ani._set_value(self.sprite, "x", 100)
        self.sprite.x.assert_called_once_with(100)

    def test_callback(self):
        callback = MagicMock()
        self.ani.schedule(callback, ScheduleType.ON_FINISH)
        self.ani.start(MagicMock())
        self.ani.finish()
        callback.assert_called_once()

    def test_update_callback(self):
        update_callback = MagicMock()
        self.ani.schedule(update_callback, ScheduleType.ON_UPDATE)
        self.ani.start(MagicMock())
        self.ani.update(1000)
        self.assertGreater(update_callback.call_count, 0)

    def test_delay(self):
        self.ani.delay = 1000
        self.ani.start(self.sprite)
        for _ in range(11):  # update 11 times to exceed delay
            self.ani.update(100)
        self.assertGreater(self.ani._elapsed, 0)

    def test_relative(self):
        self.ani = Animation(
            x=100, y=100, duration=1000, relative=True, initial=0
        )
        self.ani.start(self.sprite)
        self.ani.finish()
        self.sprite.x.assert_called_with(100)
        self.sprite.y.assert_called_with(100)

    def test_round_values(self):
        self.ani = Animation(x=100.5, y=100.5, duration=1, round_values=True)
        self.ani.start(self.sprite)
        self.ani.finish()
        self.assertEqual(self.sprite.x.call_args.args[0], 100)
        self.assertEqual(self.sprite.y.call_args.args[0], 100)
