# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pytest

from tuxemon.status.lifecycle import Lifecycle


@pytest.mark.parametrize(
    "duration, initial_turn, expected_turn",
    [
        (0, 0, 0),  # duration = 0 → never increments
        (1, 0, 1),  # increments when duration > 0
        (5, 3, 4),
    ],
)
def test_tick_turn(duration, initial_turn, expected_turn):
    lc = Lifecycle(duration=duration)
    lc.turn = initial_turn

    lc.tick_turn()

    assert lc.turn == expected_turn


@pytest.mark.parametrize(
    "duration, turn, expected",
    [
        (0, 0, False),  # infinite duration → never expires
        (3, 0, False),
        (3, 3, False),  # equal is NOT exceeded
        (3, 4, True),  # exceeded
    ],
)
def test_has_exceeded_duration(duration, turn, expected):
    lc = Lifecycle(duration=duration)
    lc.turn = turn

    assert lc.has_exceeded_duration() is expected


@pytest.mark.parametrize(
    "max_uses, increments, expected",
    [
        (1, 0, False),
        (1, 1, True),
        (2, 1, False),
        (2, 2, True),
        (3, 5, True),
    ],
)
def test_use_expiration(max_uses, increments, expected):
    lc = Lifecycle()

    for _ in range(increments):
        lc.advance_use()

    assert lc.is_use_expired(max_uses=max_uses) is expected


@pytest.mark.parametrize(
    "initial_stack, max_stacks, expected_new_stack",
    [
        (1, 5, 2),
        (4, 5, 5),
        (5, 5, 5),  # capped
        (3, 3, 3),  # capped at 3
    ],
)
def test_stack_increments_and_caps(
    initial_stack, max_stacks, expected_new_stack
):
    lc = Lifecycle(max_stacks=max_stacks)
    lc.stack_level = initial_stack

    old, new = lc.stack()

    assert old == initial_stack
    assert new == expected_new_stack


def test_stack_resets_turn_and_use_counter():
    lc = Lifecycle(max_stacks=5)
    lc.turn = 7
    lc.use_counter = 3

    lc.stack()

    assert lc.turn == 0
    assert lc.use_counter == 0
