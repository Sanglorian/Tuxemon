# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.db import Direction
from tuxemon.entity import Body, EntityState, Mover
from tuxemon.math import Point3, Vector3
from tuxemon.prepare import CONFIG


class TestMover(unittest.TestCase):
    def setUp(self):
        self.body = Body(position=Point3(0, 0, 0))
        self.mover = Mover(self.body)

    def test_initial_state(self):
        self.assertEqual(self.mover.state, EntityState.IDLE)
        self.assertEqual(self.mover.facing, Direction.down)
        self.assertEqual(self.body.velocity, Vector3(0, 0, 0))

    def test_move_sets_state_to_walking(self):
        self.mover.base_moverate = 5
        self.mover.move(Direction.right)
        self.assertEqual(self.mover.state, EntityState.WALKING)
        self.assertEqual(self.body.velocity, Vector3(5, 0, 0))

    def test_running_sets_state_and_speed(self):
        self.mover.base_moverate = 5
        self.mover.move(Direction.up)
        self.mover.running()
        self.assertEqual(self.mover.state, EntityState.RUNNING)
        self.assertEqual(self.mover.base_moverate, CONFIG.player_runrate)

    def test_walking_resets_state_and_speed(self):
        self.mover.base_moverate = CONFIG.player_runrate
        self.mover.move(Direction.left)
        self.mover.walking()
        self.assertEqual(self.mover.state, EntityState.WALKING)
        self.assertEqual(self.mover.base_moverate, CONFIG.player_walkrate)

    def test_stop_resets_velocity_and_state(self):
        self.mover.base_moverate = 5
        self.mover.move(Direction.right)
        self.mover.stop()
        self.assertEqual(self.mover.state, EntityState.IDLE)
        self.assertEqual(self.body.velocity, Vector3(0, 0, 0))

    def test_jump_applies_vertical_impulse(self):
        self.mover.jump(strength=10.0)
        self.assertEqual(self.mover.state, EntityState.JUMPING)
        self.assertEqual(self.body.velocity.z, 10.0)
        self.assertEqual(self.body.acceleration.z, Mover.GRAVITY)

    def test_jump_blocked_if_already_jumping(self):
        self.mover.jump(strength=5.0)
        initial_velocity = self.body.velocity.z
        self.mover.jump(strength=20.0)  # should be ignored
        self.assertEqual(self.body.velocity.z, initial_velocity)

    def test_apply_gravity_airborne(self):
        self.body.position.z = 5
        self.mover.apply_gravity()
        self.assertEqual(self.body.acceleration.z, Mover.GRAVITY)

    def test_apply_gravity_grounded(self):
        self.body.position.z = 0
        self.body.velocity.z = 5
        self.mover.apply_gravity()
        self.assertEqual(self.body.acceleration.z, 0)

    def test_update_movement_state_running(self):
        self.mover.base_moverate = 5
        self.mover.move(Direction.right)
        self.mover.update_movement_state(running=True)
        self.assertEqual(self.mover.state, EntityState.RUNNING)

    def test_update_movement_state_walking(self):
        self.mover.base_moverate = 5
        self.mover.move(Direction.right)
        self.mover.update_movement_state(running=False)
        self.assertEqual(self.mover.state, EntityState.WALKING)

    def test_update_movement_state_idle(self):
        self.mover.stop()
        self.mover.update_movement_state(running=True)
        self.assertEqual(self.mover.state, EntityState.IDLE)

    def test_set_state_blocks_jump_to_walk_or_run(self):
        self.mover.jump(strength=5.0)
        self.assertEqual(self.mover.state, EntityState.JUMPING)
        self.mover.set_state(EntityState.WALKING)
        self.assertEqual(self.mover.state, EntityState.JUMPING)
        self.mover.set_state(EntityState.RUNNING)
        self.assertEqual(self.mover.state, EntityState.JUMPING)

    def test_set_state_idle_resets_velocity_and_rate(self):
        self.mover.base_moverate = 10
        self.mover.move(Direction.right)
        self.assertNotEqual(self.body.velocity, Vector3(0, 0, 0))
        self.mover.set_state(EntityState.IDLE)
        self.assertEqual(self.mover.state, EntityState.IDLE)
        self.assertEqual(self.body.velocity, Vector3(0, 0, 0))
        self.assertEqual(self.mover.base_moverate, CONFIG.player_walkrate)

    def test_set_state_same_state_no_change(self):
        self.mover.move(Direction.right)
        self.assertEqual(self.mover.state, EntityState.WALKING)
        self.mover.set_state(EntityState.WALKING)
        self.assertEqual(self.mover.state, EntityState.WALKING)
