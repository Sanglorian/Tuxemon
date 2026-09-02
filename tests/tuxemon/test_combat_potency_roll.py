# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.combat.session import CombatSession
from tuxemon.core.effects.give import GiveEffect
from tuxemon.core.effects.remove import RemoveEffect
from tuxemon.core.effects.scope import ScopeEffect
from tuxemon.core.effects.statchange import StatChangeEffect
from tuxemon.core.effects.switch import SwitchEffect
from tuxemon.monster.monster import Monster


@pytest.fixture
def combat_session():
    return CombatSession()


@pytest.fixture
def monsters():
    return MagicMock(spec=Monster), MagicMock(spec=Monster)


def test_unknown_monster_defaults_to_zero(combat_session, monsters):
    # A monster with no cached roll must fail open, mirroring get_tech_hit:
    # `tech.potency >= 0.0` is always true, so a monster that entered the
    # field after the round's rolls were made is never silently disabled.
    user, _ = monsters
    assert combat_session.get_tech_potency(user) == 0.0


def test_set_and_get_explicit_value(combat_session, monsters):
    user, _ = monsters
    combat_session.set_tech_potency(user, 0.42)
    assert combat_session.get_tech_potency(user) == 0.42


def test_get_does_not_reroll(combat_session, monsters):
    # The whole point of the cache: repeated reads within a round return the
    # same value, so every potency-gated effect of one technique shares it.
    user, _ = monsters
    combat_session.set_tech_potency(user)
    first = combat_session.get_tech_potency(user)
    assert all(
        combat_session.get_tech_potency(user) == first for _ in range(20)
    )


def test_initialize_rolls_once_per_active_monster(combat_session, monsters):
    user, other = monsters
    combat_session.field_monsters = MagicMock()
    combat_session.field_monsters.active_monsters = [user, other]

    combat_session.initialize_potency_chances()

    for monster in (user, other):
        value = combat_session.get_tech_potency(monster)
        assert 0.0 <= value < 1.0


def test_monsters_roll_independently(combat_session, monsters):
    user, other = monsters
    combat_session.set_tech_potency(user, 0.1)
    combat_session.set_tech_potency(other, 0.9)
    assert combat_session.get_tech_potency(user) == 0.1
    assert combat_session.get_tech_potency(other) == 0.9


def test_potency_and_hit_caches_are_independent(combat_session, monsters):
    # Accuracy and potency stay separate gates. In particular, multiattack
    # re-rolls accuracy per swing via set_tech_hit() and must not disturb the
    # potency roll.
    user, _ = monsters
    combat_session.set_tech_potency(user, 0.25)
    combat_session.set_tech_hit(user, 0.75)

    assert combat_session.get_tech_potency(user) == 0.25
    assert combat_session.get_tech_hit(user) == 0.75

    combat_session.set_tech_hit(user, 0.99)
    assert combat_session.get_tech_potency(user) == 0.25


def test_clear_tech_potencies(combat_session, monsters):
    user, _ = monsters
    combat_session.set_tech_potency(user, 0.5)
    combat_session.clear_tech_potencies()
    assert combat_session.get_tech_potency(user) == 0.0


def test_reset_clears_both_caches(combat_session, monsters):
    user, _ = monsters
    combat_session.set_tech_potency(user, 0.5)
    combat_session.set_tech_hit(user, 0.5)

    combat_session.reset()

    assert combat_session.get_tech_potency(user) == 0.0
    assert combat_session.get_tech_hit(user) == 0.0


def _make_session(potency_roll, hit_roll):
    session = MagicMock()
    combat = session.client.combat_session
    combat.get_tech_potency.return_value = potency_roll
    combat.get_tech_hit.return_value = hit_roll
    combat.get_target_monsters.return_value = []
    return session


def _make_tech(potency, accuracy):
    tech = MagicMock()
    tech.potency = potency
    tech.accuracy = accuracy
    tech.name = "test_tech"
    return tech


@pytest.mark.parametrize(
    "effect",
    [
        pytest.param(
            GiveEffect(condition="enraged", objectives="enemy_monster"),
            id="give",
        ),
        pytest.param(
            RemoveEffect(status="all", objectives="own_monster"),
            id="remove",
        ),
    ],
)
def test_effect_reads_cached_potency(effect, monsters):
    user, target = monsters
    session = _make_session(potency_roll=0.9, hit_roll=0.0)
    tech = _make_tech(potency=0.5, accuracy=1.0)

    # 0.5 >= 0.9 is false, so the gate fails — and because the roll is cached
    # rather than drawn per call, it fails on every invocation. With a
    # per-effect random.random() this would succeed roughly half the time.
    for _ in range(50):
        result = effect.apply_tech_target(session, tech, user, target)
        assert not result.success

    session.client.combat_session.get_tech_potency.assert_called_with(user)


@pytest.mark.parametrize(
    "effect",
    [
        pytest.param(
            GiveEffect(condition="enraged", objectives="enemy_monster"),
            id="give",
        ),
        pytest.param(
            RemoveEffect(status="all", objectives="own_monster"),
            id="remove",
        ),
    ],
)
def test_effect_passes_potency_gate_on_favourable_roll(effect, monsters):
    user, target = monsters
    session = _make_session(potency_roll=0.4, hit_roll=0.0)
    tech = _make_tech(potency=0.5, accuracy=1.0)

    effect.apply_tech_target(session, tech, user, target)

    # The gate opened, so the effect went on to resolve its targets.
    session.client.combat_session.get_target_monsters.assert_called()


@pytest.mark.parametrize(
    "effect",
    [
        pytest.param(
            StatChangeEffect(objectives="own_monster"), id="statchange"
        ),
        pytest.param(ScopeEffect(), id="scope"),
        pytest.param(
            SwitchEffect(objectives="enemy_monster", element="fire"),
            id="switch",
        ),
    ],
)
def test_newly_gated_effect_fails_on_unfavourable_potency(effect, monsters):
    user, target = monsters
    session = _make_session(potency_roll=0.9, hit_roll=0.0)
    tech = _make_tech(potency=0.5, accuracy=1.0)

    for _ in range(50):
        result = effect.apply_tech_target(session, tech, user, target)
        assert not result.success


@pytest.mark.parametrize(
    "effect",
    [
        pytest.param(
            StatChangeEffect(objectives="own_monster"), id="statchange"
        ),
        pytest.param(ScopeEffect(), id="scope"),
    ],
)
def test_newly_gated_effect_succeeds_on_favourable_potency(effect, monsters):
    user, target = monsters
    session = _make_session(potency_roll=0.4, hit_roll=0.0)
    tech = _make_tech(potency=0.5, accuracy=1.0)

    assert effect.apply_tech_target(session, tech, user, target).success


def test_switch_still_gated_on_accuracy(monsters):
    # Potency is an additional gate, not a replacement: a miss still fails
    # even when the potency roll is favourable.
    user, target = monsters
    effect = SwitchEffect(objectives="enemy_monster", element="fire")
    session = _make_session(potency_roll=0.0, hit_roll=0.9)
    tech = _make_tech(potency=1.0, accuracy=0.5)

    assert not effect.apply_tech_target(session, tech, user, target).success


def test_statchange_status_path_is_not_gated():
    # statchange also runs as a status effect, where there is no technique to
    # roll against. That path must always apply.
    effect = StatChangeEffect(objectives="own_monster")
    status = MagicMock()
    status.name = "focused"
    status.is_already_applied.return_value = False

    result = effect.apply_status(MagicMock(), status)

    assert result.success


def test_statchange_item_path_is_not_gated():
    effect = StatChangeEffect(objectives="own_monster")
    item = MagicMock()
    item.name = "boost_speed"

    result = effect.apply_item_target(
        MagicMock(), item, MagicMock(spec=Monster)
    )

    assert result.success
