# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.core.effects.regenerate import RegenerateEffect
from tuxemon.db import EffectPhase
from tuxemon.item.item import Item
from tuxemon.monster.monster import Monster


def make_item(phase):
    item = MagicMock(spec=Item)
    item.name = "Life Gem"
    item.has_phase.side_effect = lambda other: other == phase
    return item


def make_target(hp, current_hp):
    target = MagicMock(spec=Monster)
    target.name = "Rockitten"
    target.hp = hp
    target.current_hp = current_hp
    target.missing_hp = max(min(hp - current_hp, hp), 0)
    return target


@pytest.fixture
def effect():
    return RegenerateEffect(divisor=16)


@pytest.fixture
def session():
    return MagicMock()


def test_heals_a_fraction_of_max_hp(effect, session):
    item = make_item(EffectPhase.END_OF_ROUND)
    target = make_target(hp=160, current_hp=100)

    result = effect.apply_item_target(session, item, target)

    assert result.success
    assert target.current_hp == 110
    assert result.extras


def test_heal_is_capped_at_max_hp(effect, session):
    item = make_item(EffectPhase.END_OF_ROUND)
    target = make_target(hp=160, current_hp=157)

    result = effect.apply_item_target(session, item, target)

    assert result.success
    assert target.current_hp == 160


def test_no_heal_at_full_hp(effect, session):
    item = make_item(EffectPhase.END_OF_ROUND)
    target = make_target(hp=160, current_hp=160)

    result = effect.apply_item_target(session, item, target)

    assert not result.success
    assert not result.extras
    assert target.current_hp == 160


def test_no_heal_when_max_hp_is_below_the_divisor(session):
    effect = RegenerateEffect(divisor=16)
    item = make_item(EffectPhase.END_OF_ROUND)
    target = make_target(hp=10, current_hp=1)

    result = effect.apply_item_target(session, item, target)

    assert not result.success
    assert target.current_hp == 1


@pytest.mark.parametrize(
    "phase",
    [
        pytest.param(EffectPhase.DEFAULT, id="default"),
        pytest.param(EffectPhase.ON_DECISION, id="on_decision"),
        pytest.param(EffectPhase.PERFORM_ITEM, id="perform_item"),
    ],
)
def test_no_heal_outside_the_end_of_round(effect, session, phase):
    item = make_item(phase)
    target = make_target(hp=160, current_hp=100)

    result = effect.apply_item_target(session, item, target)

    assert not result.success
    assert not result.extras
    assert target.current_hp == 100
