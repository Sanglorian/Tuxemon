# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pytest

from tuxemon.technique.cooldown import Cooldown


def test_initial_state():
    cd = Cooldown(duration=3)
    assert cd.duration == 3
    assert cd.remaining == 0
    assert cd.is_recharging is False


@pytest.mark.parametrize("duration", [0, 1, 5, 999])
def test_trigger_sets_remaining_to_duration(duration):
    cd = Cooldown(duration=duration)
    cd.trigger()
    assert cd.remaining == duration
    assert cd.is_recharging is (duration > 0)


@pytest.mark.parametrize(
    "start, tick_amount, expected",
    [
        (5, 1, 4),
        (5, 2, 3),
        (1, 5, 0),  # cannot go below zero
        (0, 1, 0),  # already zero
    ],
)
def test_tick_reduces_remaining(start, tick_amount, expected):
    cd = Cooldown(duration=10)
    cd.remaining = start
    cd.tick(tick_amount)
    assert cd.remaining == expected


def test_reset_sets_remaining_to_zero():
    cd = Cooldown(duration=3)
    cd.remaining = 3
    cd.reset()
    assert cd.remaining == 0
    assert cd.is_recharging is False


@pytest.mark.parametrize(
    "initial, add_amount, max_value, expected",
    [
        (0, 1, 5, 1),
        (1, 2, 5, 3),
        (3, 10, 5, 5),  # clamp
        (5, 1, 5, 5),  # already max
    ],
)
def test_add_increases_remaining_but_clamps(
    initial, add_amount, max_value, expected
):
    cd = Cooldown(duration=3)
    cd.remaining = initial
    cd.add(add_amount, max_value)
    assert cd.remaining == expected


def test_trigger_overrides_remaining():
    cd = Cooldown(duration=4)
    cd.remaining = 99
    cd.trigger()
    assert cd.remaining == 4


def test_negative_tick_does_not_increase_remaining():
    cd = Cooldown(duration=5)
    cd.remaining = 3
    cd.tick(-10)
    assert cd.remaining == 3  # unchanged


def test_negative_add_does_not_reduce_remaining():
    cd = Cooldown(duration=5)
    cd.remaining = 3
    cd.add(-5, max_value=10)
    assert cd.remaining == 3  # unchanged
