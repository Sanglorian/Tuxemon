# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock, patch

import pytest

from tuxemon.core.asset import init_assets
from tuxemon.db import EffectPhase
from tuxemon.event.actions.set_monster_status import SetMonsterStatusAction
from tuxemon.monster.status import MonsterStatusHandler

set_status = SetMonsterStatusAction.set_status


@pytest.fixture
def session():
    init_assets()
    return MagicMock()


def make_monster(immune=False):
    monster = MagicMock()
    monster.name = "Rockitten"
    monster.status = MonsterStatusHandler()
    monster.held_item = MagicMock()
    monster.held_item.is_immune.return_value = immune
    return monster


@patch("tuxemon.status.status.StatusModel.lookup")
def test_setting_a_status_runs_on_start(mock_lookup, session, status_model):
    """
    ON_START is the only place a status applies its stat modifiers, so a
    scripted status that skips it has no effect on the monster.
    """
    mock_lookup.return_value = status_model(slug="enraged")
    monster = make_monster()

    set_status(session, monster, "enraged", 0.0)

    assert monster.status.has_status("enraged")
    added = monster.status.current_status
    assert added.phase == EffectPhase.ON_START


@patch("tuxemon.status.status.StatusModel.lookup")
def test_replacing_a_status_ends_the_old_one(
    mock_lookup, session, status_model
):
    mock_lookup.return_value = status_model(slug="enraged")
    monster = make_monster()
    displaced = MagicMock(slug="poison", category=None)
    displaced.host = monster
    monster.status.add_status(displaced)

    set_status(session, monster, "enraged", 0.0)

    displaced.use.assert_any_call(session, EffectPhase.ON_END)
    assert monster.status.has_status("enraged")


@patch("tuxemon.status.status.StatusModel.lookup")
def test_immune_monster_keeps_its_status(mock_lookup, session, status_model):
    mock_lookup.return_value = status_model(slug="poison")
    monster = make_monster(immune=True)

    set_status(session, monster, "poison", 0.0)

    assert not monster.status.status_exists()


def test_omitting_the_status_clears_it(session):
    monster = make_monster()
    existing = MagicMock(slug="poison")
    existing.host = monster
    monster.status.add_status(existing)

    set_status(session, monster, None, 0.0)

    assert not monster.status.status_exists()
    existing.use.assert_any_call(session, EffectPhase.ON_END)
