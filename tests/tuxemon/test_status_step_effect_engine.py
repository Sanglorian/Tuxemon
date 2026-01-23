# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pytest

from tuxemon.db import StepEffectType
from tuxemon.status.step_effect_engine import StepEffectEngine


class DummyMonster:
    def __init__(self, hp, current_hp=None):
        self.hp = hp
        self.current_hp = current_hp if current_hp is not None else hp


@pytest.mark.parametrize(
    "interval, initial_steps, added, expected_ticks",
    [
        (0, 0, 10, 0),  # interval disabled
        (5, 0, 4, 0),  # not enough to trigger
        (5, 0, 5, 1),  # exactly one interval
        (5, 3, 4, 1),  # crosses from 3→7
        (5, 0, 12, 2),  # two intervals
        (3, 2, 10, 3),  # 2→12 crosses 3,6,9
    ],
)
def test_add_steps(interval, initial_steps, added, expected_ticks):
    engine = StepEffectEngine(interval=interval, initial_steps=initial_steps)
    ticks = engine.add_steps(added)
    assert ticks == expected_ticks


@pytest.mark.parametrize(
    "value, ticks, expected",
    [
        (5, 1, -5),
        (5, 3, -15),
        (0, 10, 0),  # zero value → no change
    ],
)
def test_compute_hp_change_flat_damage(value, ticks, expected):
    m = DummyMonster(hp=100)
    engine = StepEffectEngine(
        effect_type=StepEffectType.FLAT_DAMAGE,
        value=value,
    )
    assert engine.compute_hp_change(m, ticks) == expected


@pytest.mark.parametrize(
    "hp, percent, ticks, expected",
    [
        (100, 10, 1, -10),
        (200, 25, 2, -100),  # 25% of 200 = 50 per tick
    ],
)
def test_compute_hp_change_percent_max_hp_damage(hp, percent, ticks, expected):
    m = DummyMonster(hp=hp)
    engine = StepEffectEngine(
        effect_type=StepEffectType.PERCENT_MAX_HP_DAMAGE,
        value=percent,
    )
    assert engine.compute_hp_change(m, ticks) == expected


@pytest.mark.parametrize(
    "current_hp, percent, ticks, expected",
    [
        (100, 10, 1, -10),
        (80, 50, 2, -80),  # 50% of 80 = 40 per tick
    ],
)
def test_compute_hp_change_percent_current_hp_damage(
    current_hp, percent, ticks, expected
):
    m = DummyMonster(hp=100, current_hp=current_hp)
    engine = StepEffectEngine(
        effect_type=StepEffectType.PERCENT_CURRENT_HP_DAMAGE,
        value=percent,
    )
    assert engine.compute_hp_change(m, ticks) == expected


@pytest.mark.parametrize(
    "hp, percent, ticks, expected",
    [
        (100, 10, 1, 10),
        (200, 25, 2, 100),  # 25% of 200 = 50 per tick
    ],
)
def test_compute_hp_change_percent_max_hp_heal(hp, percent, ticks, expected):
    m = DummyMonster(hp=hp)
    engine = StepEffectEngine(
        effect_type=StepEffectType.PERCENT_MAX_HP_HEAL,
        value=percent,
    )
    assert engine.compute_hp_change(m, ticks) == expected


@pytest.mark.parametrize(
    "current_hp, percent, ticks, expected",
    [
        (100, 10, 1, 10),
        (80, 50, 2, 80),  # 50% of 80 = 40 per tick
    ],
)
def test_compute_hp_change_percent_current_hp_heal(
    current_hp, percent, ticks, expected
):
    m = DummyMonster(hp=100, current_hp=current_hp)
    engine = StepEffectEngine(
        effect_type=StepEffectType.PERCENT_CURRENT_HP_HEAL,
        value=percent,
    )
    assert engine.compute_hp_change(m, ticks) == expected


@pytest.mark.parametrize(
    "effect_type, value",
    [
        (StepEffectType.NONE, 10),
        (StepEffectType.FLAT_DAMAGE, 0),
        (StepEffectType.PERCENT_MAX_HP_DAMAGE, 0),
    ],
)
def test_compute_hp_change_none_or_zero(effect_type, value):
    m = DummyMonster(hp=100)
    engine = StepEffectEngine(effect_type=effect_type, value=value)
    assert engine.compute_hp_change(m, ticks=5) == 0
