# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock, patch

import pytest

from tuxemon.core.asset import init_assets
from tuxemon.core.effects.transfer import TransferEffect
from tuxemon.db import EffectPhase
from tuxemon.monster.status import MonsterStatusHandler
from tuxemon.status.status import Status


@pytest.fixture
def session():
    init_assets()
    session = MagicMock()
    session.client.combat_session.get_tech_hit.return_value = 0.0
    return session


@pytest.fixture
def tech():
    technique = MagicMock()
    technique.accuracy = 1.0
    technique.name = "Suck Poison"
    return technique


def make_monster(name, immune=False):
    monster = MagicMock()
    monster.name = name
    monster.steps = 0.0
    monster.status = MonsterStatusHandler()
    monster.held_item = MagicMock()
    monster.held_item.name = "Tomato Berry"
    monster.held_item.is_immune.return_value = immune
    return monster


@pytest.fixture
def transfer():
    return TransferEffect(condition="poison", direction="user_to_target")


@patch("tuxemon.status.status.StatusModel.lookup")
def test_condition_moves_to_the_destination(
    mock_lookup, session, tech, transfer, status_model
):
    mock_lookup.return_value = status_model(gain_cond="{target} is poisoned.")
    user = make_monster("Nudimind")
    target = make_monster("Rockitten")
    user.status.add_status(Status.create("poison", user))

    result = transfer.apply_tech_target(session, tech, user, target)

    assert result.success
    assert not user.status.has_status("poison")
    assert target.status.has_status("poison")
    assert result.extras == ["Rockitten is poisoned."]


@patch("tuxemon.status.status.StatusModel.lookup")
def test_displaced_status_is_ended_not_dropped(
    mock_lookup, session, tech, transfer, status_model
):
    """
    The destination's existing status has to run its ON_END hook, or effects
    that mutate the monster (stat modifiers, move stats) never revert.
    """
    mock_lookup.return_value = status_model()
    user = make_monster("Nudimind")
    target = make_monster("Rockitten")
    user.status.add_status(Status.create("poison", user))
    displaced = MagicMock(slug="grabbed", category=None)
    displaced.host = target
    target.status.add_status(displaced)

    transfer.apply_tech_target(session, tech, user, target)

    displaced.use.assert_any_call(session, EffectPhase.ON_END)


@patch("tuxemon.status.status.StatusModel.lookup")
def test_condition_is_destroyed_when_destination_is_immune(
    mock_lookup, session, tech, transfer, status_model
):
    """Transferring onto an immune monster is a valid way to lose it."""
    mock_lookup.return_value = status_model()
    user = make_monster("Nudimind")
    target = make_monster("Rockitten", immune=True)
    user.status.add_status(Status.create("poison", user))

    result = transfer.apply_tech_target(session, tech, user, target)

    assert result.success
    assert not user.status.has_status("poison")
    assert not target.status.has_status("poison")
    assert result.extras == ["Rockitten (Tomato Berry) is immune to Poison"]


@patch("tuxemon.status.status.StatusModel.lookup")
def test_nothing_happens_without_the_condition(
    mock_lookup, session, tech, transfer, status_model
):
    mock_lookup.return_value = status_model()
    user = make_monster("Nudimind")
    target = make_monster("Rockitten")

    result = transfer.apply_tech_target(session, tech, user, target)

    assert not result.success
    assert not target.status.status_exists()
    assert result.extras == []


@patch("tuxemon.status.status.StatusModel.lookup")
def test_miss_leaves_both_monsters_alone(
    mock_lookup, session, tech, transfer, status_model
):
    mock_lookup.return_value = status_model()
    session.client.combat_session.get_tech_hit.return_value = 2.0
    user = make_monster("Nudimind")
    target = make_monster("Rockitten")
    user.status.add_status(Status.create("poison", user))

    result = transfer.apply_tech_target(session, tech, user, target)

    assert not result.success
    assert user.status.has_status("poison")
    assert not target.status.status_exists()
