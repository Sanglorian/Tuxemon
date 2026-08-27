# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.combat.session import CombatSession
from tuxemon.core.core_effect import ItemEffectResult
from tuxemon.db import EffectPhase


def make_player(fainted=False):
    player = MagicMock()
    player.party.is_fainted = fainted
    return player


def make_monster(owner, item=None):
    monster = MagicMock()
    monster.held_item = item
    monster.get_owner.return_value = owner
    return monster


def make_item(success=True, extras=None):
    item = MagicMock()
    item.use.return_value = ItemEffectResult(
        name="Life Gem", success=success, extras=extras or []
    )
    return item


@pytest.fixture
def combat():
    combat = CombatSession()
    combat._players = [make_player(), make_player()]
    return combat


def test_held_items_are_used_at_the_end_of_the_round(combat):
    left, right = combat.players
    item = make_item(extras=["healed"])
    monster = make_monster(left, item)
    combat.field_monsters.add_monster(left, monster)
    combat.field_monsters.add_monster(right, make_monster(right))

    results = combat.apply_held_items(MagicMock())

    assert len(results) == 1
    _, _, target, phase = item.use.call_args.args
    assert target is monster
    assert phase == EffectPhase.END_OF_ROUND


def test_monsters_without_a_held_item_are_skipped(combat):
    left, right = combat.players
    combat.field_monsters.add_monster(left, make_monster(left))
    combat.field_monsters.add_monster(right, make_monster(right))

    assert combat.apply_held_items(MagicMock()) == []


def test_held_items_that_do_nothing_are_not_reported(combat):
    left, _ = combat.players
    item = make_item(success=False)
    combat.field_monsters.add_monster(left, make_monster(left, item))

    assert combat.apply_held_items(MagicMock()) == []
    assert item.use.called


def test_held_items_are_not_used_once_the_battle_is_over(combat):
    left, right = combat.players
    right.party.is_fainted = True
    item = make_item(extras=["healed"])
    combat.field_monsters.add_monster(left, make_monster(left, item))

    assert combat.apply_held_items(MagicMock()) == []
    assert not item.use.called
