# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import logging
from unittest.mock import MagicMock, patch

import pytest

from tuxemon.core.asset import init_assets
from tuxemon.db import CategoryStatus, EffectPhase, ResponseStatus
from tuxemon.event.actions.set_monster_status import SetMonsterStatusAction
from tuxemon.monster.status import MonsterStatusHandler
from tuxemon.status.status import Status


def make_status(slug, host, category=CategoryStatus.NEGATIVE):
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
    model.on_negative_status = ResponseStatus.REPLACED
    model.category = category
    with patch("tuxemon.status.status.StatusModel.lookup", return_value=model):
        status = Status.create(slug, host)
    status.use = MagicMock()
    return status


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def monster():
    mon = MagicMock()
    mon.name = "Rockitten"
    mon.held_item = None
    mon.status = MonsterStatusHandler()
    return mon


def set_status(session, monster, value, incoming):
    with patch(
        "tuxemon.event.actions.set_monster_status.Status.create",
        return_value=incoming,
    ):
        SetMonsterStatusAction.set_status(session, monster, value, 0.0)


def test_apply_runs_on_start(session, monster):
    enraged = make_status("enraged", monster, CategoryStatus.POSITIVE)

    set_status(session, monster, "enraged", enraged)

    assert monster.status.current_status is enraged
    enraged.use.assert_called_once_with(session, EffectPhase.ON_START)


def test_replacing_ends_previous_status(session, monster):
    grabbed = make_status("grabbed", monster)
    monster.status.status = [grabbed]
    enraged = make_status("enraged", monster, CategoryStatus.POSITIVE)

    set_status(session, monster, "enraged", enraged)

    grabbed.use.assert_called_once_with(session, EffectPhase.ON_END)
    assert monster.status.current_status is enraged


def test_immune_monster_is_left_alone(session, monster, caplog):
    monster.held_item = MagicMock()
    monster.held_item.is_immune.return_value = True
    monster.held_item.name = "Antidote Charm"
    poison = make_status("poison", monster)

    with caplog.at_level(
        logging.INFO, logger="tuxemon.event.actions.set_monster_status"
    ):
        set_status(session, monster, "poison", poison)

    assert not monster.status.status_exists()
    poison.use.assert_not_called()
    assert "immune_by_item" in caplog.text
    assert "Antidote Charm" in caplog.text


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(None, id="omitted"),
        pytest.param("", id="empty"),
    ],
)
def test_omitting_status_clears(session, monster, value):
    poison = make_status("poison", monster)
    monster.status.status = [poison]

    with patch(
        "tuxemon.event.actions.set_monster_status.Status.create"
    ) as create:
        SetMonsterStatusAction.set_status(session, monster, value, 0.0)

    create.assert_not_called()
    assert not monster.status.status_exists()
    poison.use.assert_called_once_with(session, EffectPhase.ON_END)
