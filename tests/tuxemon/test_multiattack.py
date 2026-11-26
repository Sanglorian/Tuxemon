# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import Mock, patch

import pytest

from tuxemon.core.core_effect import CoreEffect, TechEffectResult
from tuxemon.core.core_processor import EffectProcessor
from tuxemon.core.effects.multiattack import MultiAttackEffect


class StubCombatSession:
    """Minimal stand-in for the combat session's tech hit bookkeeping."""

    def __init__(self, rolls):
        # rolls consumed one per set_tech_hit() call
        self._rolls = list(rolls)
        self._tech_hit = {}

    def set_tech_hit(self, monster, value=None):
        if value is None:
            value = self._rolls.pop(0)
        self._tech_hit[monster] = value

    def get_tech_hit(self, monster):
        return self._tech_hit.get(monster, 0.0)


class StubMonster:
    def __init__(self, hp=100, current_hp=None):
        self.name = "Target"
        self.hp = hp
        self.current_hp = hp if current_hp is None else current_hp
        self.status = Mock()
        self.status.current_status = None

    @property
    def is_fainted(self):
        return self.current_hp <= 0


@pytest.fixture
def technique():
    tech = Mock()
    tech.name = "Air Chain"
    tech.accuracy = 0.8
    return tech


@pytest.fixture
def user():
    return StubMonster()


def make_session(rolls, original_hit=0.1):
    session = Mock()
    combat = StubCombatSession(rolls)
    session.client.combat_session = combat
    return session, combat


def apply(effect, session, technique, user, target):
    with patch(
        "tuxemon.core.effects.multiattack.formula.simple_damage_calculate",
        return_value=(10, 1.0),
    ):
        return effect.apply_tech_target(session, technique, user, target)


def test_all_hits_land(technique, user):
    session, _ = make_session([0.1, 0.2, 0.3])
    target = StubMonster(hp=100)

    result = apply(MultiAttackEffect(3), session, technique, user, target)

    assert result.hit_count == 3
    assert result.hit_damages == [10, 10, 10]
    assert result.damage == 30
    assert result.success
    assert result.should_tackle
    assert target.current_hp == 70


def test_stops_on_first_miss(technique, user):
    # second roll is above the technique's accuracy
    session, _ = make_session([0.1, 0.95, 0.1])
    target = StubMonster(hp=100)

    result = apply(MultiAttackEffect(3), session, technique, user, target)

    assert result.hit_count == 1
    assert result.hit_damages == [10]
    assert result.damage == 10
    assert target.current_hp == 90


def test_first_hit_misses(technique, user):
    session, _ = make_session([0.95])
    target = StubMonster(hp=100)

    result = apply(MultiAttackEffect(3), session, technique, user, target)

    assert result.hit_count == 0
    assert result.hit_damages == []
    assert result.damage == 0
    assert not result.success
    assert not result.should_tackle
    assert result.extras == []
    assert target.current_hp == 100


def test_stops_once_target_faints(technique, user):
    session, _ = make_session([0.1, 0.2, 0.3, 0.4, 0.5])
    # only 25 HP left: two full hits, then a clamped 5 damage third hit
    target = StubMonster(hp=100, current_hp=25)

    result = apply(MultiAttackEffect(5), session, technique, user, target)

    assert result.hit_count == 3
    assert result.hit_damages == [10, 10, 5]
    assert sum(result.hit_damages) == result.damage
    assert result.damage == 25
    assert target.current_hp == 0


def test_no_overkill_on_exact_lethal_hit(technique, user):
    session, _ = make_session([0.1, 0.2, 0.3])
    target = StubMonster(hp=100, current_hp=20)

    result = apply(MultiAttackEffect(3), session, technique, user, target)

    assert result.hit_damages == [10, 10]
    assert result.damage == 20
    assert target.current_hp == 0


def test_tech_hit_roll_is_restored(technique, user):
    session, combat = make_session([0.1, 0.2, 0.3])
    combat.set_tech_hit(user, 0.42)
    target = StubMonster(hp=100)

    apply(MultiAttackEffect(3), session, technique, user, target)

    assert combat.get_tech_hit(user) == 0.42


def test_tech_hit_roll_is_restored_after_a_miss(technique, user):
    session, combat = make_session([0.99])
    combat.set_tech_hit(user, 0.42)
    target = StubMonster(hp=100)

    apply(MultiAttackEffect(3), session, technique, user, target)

    assert combat.get_tech_hit(user) == 0.42


def test_fainted_target_status_can_restore_hp(technique, user):
    session, _ = make_session([0.1, 0.2, 0.3])
    target = StubMonster(hp=100, current_hp=10)

    def revive(_session, _phase):
        # diehard clears itself once used, so it only saves the target once
        target.status.current_status = None
        target.current_hp = 1
        return Mock(extras=["combat_state_diehard_tech"])

    status = Mock()
    status.use.side_effect = revive
    target.status.current_status = status

    result = apply(MultiAttackEffect(3), session, technique, user, target)

    # first hit faints the target, diehard brings it back to 1 HP, the
    # second hit is clamped to that 1 HP and ends the chain
    assert result.hit_damages == [10, 1]
    assert target.current_hp == 0
    assert "combat_state_diehard_tech" in result.extras


def test_extras_reports_hit_count(technique, user):
    session, _ = make_session([0.1, 0.2])
    target = StubMonster(hp=100)

    with patch(
        "tuxemon.core.effects.multiattack.T.format",
        return_value="Hit 2 time(s)!",
    ) as mock_format:
        result = apply(MultiAttackEffect(2), session, technique, user, target)

    mock_format.assert_called_once_with("combat_multiattack", {"hit_count": 2})
    assert result.extras == ["Hit 2 time(s)!"]


# EffectProcessor merging


def test_processor_merges_hit_count_and_damages():
    session = Mock()
    technique = Mock()
    technique.name = "Air Chain"

    multiattack = Mock(spec=CoreEffect)
    multiattack.apply_tech_target.return_value = TechEffectResult(
        name="Air Chain",
        success=True,
        damage=30,
        should_tackle=True,
        hit_count=3,
        hit_damages=[10, 10, 10],
    )
    give = Mock(spec=CoreEffect)
    give.apply_tech_target.return_value = TechEffectResult(
        name="Air Chain", success=True, extras=["Slowed"]
    )
    processor = EffectProcessor([multiattack, give])

    result = processor.process_tech(session, technique, Mock(), Mock())

    assert result.hit_count == 3
    assert result.hit_damages == [10, 10, 10]
    assert result.damage == 30
    assert result.extras == ["Slowed"]


def test_processor_hit_count_defaults_to_one():
    session = Mock()
    technique = Mock()
    technique.name = "Ram"

    damage = Mock(spec=CoreEffect)
    damage.apply_tech_target.return_value = TechEffectResult(
        name="Ram", success=True, damage=12, should_tackle=True
    )
    processor = EffectProcessor([damage])

    result = processor.process_tech(session, technique, Mock(), Mock())

    assert result.hit_count == 1
    assert result.hit_damages == []
