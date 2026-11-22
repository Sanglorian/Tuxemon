# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock, patch

import pytest

from tuxemon.core.asset import init_assets
from tuxemon.core.effects.transfer import TransferEffect
from tuxemon.db import CategoryStatus, EffectPhase, ResponseStatus
from tuxemon.locale.locale import T
from tuxemon.monster.status import MonsterStatusHandler
from tuxemon.status.status import Status


def make_status(
    slug,
    host,
    category=CategoryStatus.NEGATIVE,
    on_negative_status=ResponseStatus.REPLACED,
):
    """Build a real Status from a mocked db model (avoids loading the db)."""
    init_assets()
    model = MagicMock()
    model.slug = slug
    model.conditions = []
    model.effects = []
    model.modifiers = []
    model.duration = 0
    model.max_stacks = 5
    model.step_interval = 0
    model.step_effect_value = 0.0
    model.gain_cond = None
    model.use_success = None
    model.use_failure = None
    model.on_positive_status = ResponseStatus.REPLACED
    model.on_negative_status = on_negative_status
    model.category = category
    with patch("tuxemon.status.status.StatusModel.lookup", return_value=model):
        status = Status.create(slug, host)
    status.use = MagicMock()
    return status


def make_monster(name):
    monster = MagicMock()
    monster.name = name
    monster.steps = 0.0
    monster.held_item = None
    monster.status = MonsterStatusHandler()
    return monster


def give(monster, status):
    monster.status.status = [status]


@pytest.fixture
def session():
    session = MagicMock()
    session.client.combat_session.get_tech_hit.return_value = 0.0
    return session


@pytest.fixture
def tech():
    technique = MagicMock()
    technique.name = "Suck Poison"
    technique.accuracy = 1.0
    return technique


@pytest.fixture
def user():
    return make_monster("Nudiflot")


@pytest.fixture
def target():
    return make_monster("Rockitten")


def transfer(session, tech, user, target, incoming):
    """Run ``transfer poison target_to_user``; ``incoming`` is the new
    status object the effect will create for the destination."""
    effect = TransferEffect("poison", "target_to_user")
    with patch(
        "tuxemon.core.effects.transfer.Status.create", return_value=incoming
    ):
        return effect.apply_tech_target(session, tech, user, target)


def test_condition_moves_across(session, tech, user, target):
    give(target, make_status("poison", target))
    incoming = make_status("poison", user)

    result = transfer(session, tech, user, target, incoming)

    assert result.success
    assert result.extras == []
    assert not target.status.status_exists()
    assert user.status.current_status is incoming
    incoming.use.assert_called_once_with(session, EffectPhase.ON_START)


def test_destination_previous_status_is_ended(session, tech, user, target):
    give(target, make_status("poison", target))
    grabbed = make_status("grabbed", user)
    give(user, grabbed)
    incoming = make_status("poison", user)

    result = transfer(session, tech, user, target, incoming)

    assert result.success
    grabbed.use.assert_called_once_with(session, EffectPhase.ON_END)
    assert user.status.current_status is incoming


def test_immune_destination_destroys_condition(session, tech, user, target):
    give(target, make_status("poison", target))
    user.held_item = MagicMock()
    user.held_item.is_immune.return_value = True
    user.held_item.name = "Antidote Charm"
    incoming = make_status("poison", user)

    result = transfer(session, tech, user, target, incoming)

    assert result.success
    assert not target.status.status_exists()
    assert not user.status.status_exists()
    incoming.use.assert_not_called()
    expected = T.format(
        "combat_state_immune",
        {"target": "Nudiflot (Antidote Charm)", "method": incoming.name},
    )
    assert result.extras == [expected]


def test_blocked_by_destination_status_is_reported(
    session, tech, user, target
):
    give(target, make_status("poison", target))
    sticky = make_status(
        "stuck", user, on_negative_status=ResponseStatus.BLOCKED
    )
    give(user, sticky)
    incoming = make_status("poison", user)

    result = transfer(session, tech, user, target, incoming)

    assert result.success
    assert not target.status.status_exists()
    assert user.status.current_status is sticky
    sticky.use.assert_not_called()
    expected = T.format(
        "combat_state_prevented",
        {
            "method": sticky.name,
            "target": "Nudiflot",
            "condition": incoming.name,
        },
    )
    assert result.extras == [expected]


def test_source_without_condition_changes_nothing(session, tech, user, target):
    burn = make_status("burn", target)
    give(target, burn)
    enraged = make_status("enraged", user)
    give(user, enraged)

    with patch("tuxemon.core.effects.transfer.Status.create") as create:
        effect = TransferEffect("poison", "target_to_user")
        result = effect.apply_tech_target(session, tech, user, target)

    create.assert_not_called()
    assert not result.success
    assert result.extras == []
    assert target.status.current_status is burn
    assert user.status.current_status is enraged
    burn.use.assert_not_called()
    enraged.use.assert_not_called()


def test_missed_technique_changes_nothing(session, tech, user, target):
    session.client.combat_session.get_tech_hit.return_value = 1.0
    tech.accuracy = 0.5
    poison = make_status("poison", target)
    give(target, poison)
    enraged = make_status("enraged", user)
    give(user, enraged)

    with patch("tuxemon.core.effects.transfer.Status.create") as create:
        effect = TransferEffect("poison", "target_to_user")
        result = effect.apply_tech_target(session, tech, user, target)

    create.assert_not_called()
    assert not result.success
    assert result.extras == []
    assert target.status.current_status is poison
    assert user.status.current_status is enraged
    poison.use.assert_not_called()
    enraged.use.assert_not_called()
