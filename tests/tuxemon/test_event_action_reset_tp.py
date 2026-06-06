# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from tuxemon.event.actions.reset_tp import ResetTpAction
from tuxemon.monster.stats import TrainingPoints


def make_monster(instance_id=None, **tps):
    """Build a mock monster carrying a real TrainingPoints object."""
    monster = MagicMock()
    monster.instance_id = instance_id or uuid4()
    monster.training_points = TrainingPoints(**tps)
    return monster


def make_session(monsters, selected=None, variable_value=None):
    session = MagicMock()
    session.player.monsters = monsters
    session.player.game_variables = (
        {"mon": str(variable_value)} if variable_value else {}
    )
    session.client.get_monster_by_iid.return_value = selected
    return session


def run_action(session, variable=None, stat=None):
    action = ResetTpAction(variable=variable, stat=stat)
    action.start(session)
    return action


def test_reset_single_stat_one_monster():
    monster = make_monster(armour=40, speed=30)
    session = make_session(
        [monster], selected=monster, variable_value=monster.instance_id
    )

    run_action(session, variable="mon", stat="armour")

    assert monster.training_points.armour == 0
    assert monster.training_points.speed == 30
    monster.set_stats.assert_called_once()


def test_reset_all_stats_one_monster():
    monster = make_monster(armour=40, speed=30, hp=20)
    session = make_session(
        [monster], selected=monster, variable_value=monster.instance_id
    )

    run_action(session, variable="mon")

    assert monster.training_points.sum() == 0
    monster.set_stats.assert_called_once()


def test_reset_all_stats_whole_party():
    a = make_monster(armour=40, speed=30)
    b = make_monster(hp=15, melee=25)
    session = make_session([a, b])

    run_action(session)

    assert a.training_points.sum() == 0
    assert b.training_points.sum() == 0
    a.set_stats.assert_called_once()
    b.set_stats.assert_called_once()


def test_reset_single_stat_whole_party():
    a = make_monster(armour=40, speed=30)
    b = make_monster(armour=10, hp=15)
    session = make_session([a, b])

    run_action(session, stat="speed")

    assert a.training_points.speed == 0
    assert a.training_points.armour == 40
    assert b.training_points.armour == 10


def test_invalid_stat_raises():
    monster = make_monster(armour=40)
    session = make_session([monster])

    with pytest.raises(ValueError):
        run_action(session, stat="bogus")


def test_no_monsters_stops_gracefully():
    session = make_session([])

    action = run_action(session)

    assert action._done is True


def test_invalid_uuid_does_not_touch_monsters():
    monster = make_monster(armour=40)
    session = make_session([monster])  # no variable set -> lookup fails

    run_action(session, variable="mon")

    assert monster.training_points.armour == 40
    monster.set_stats.assert_not_called()
