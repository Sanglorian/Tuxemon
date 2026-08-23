# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock, patch

import pytest

from tuxemon.core.asset import init_assets
from tuxemon.db import EffectPhase
from tuxemon.status.status import Status


@pytest.fixture
def session():
    init_assets()
    return MagicMock()


@pytest.fixture
def host():
    monster = MagicMock()
    monster.name = "Rockitten"
    monster.hp = 160
    monster.current_hp = 160
    monster.is_fainted = False
    return monster


@pytest.fixture
def wasting(status_model, host):
    """A real wasting status, built without loading the database."""
    model = status_model(
        slug="wasting",
        effects=[MagicMock(type="wasting", parameters=["16"])],
    )
    with patch("tuxemon.status.status.StatusModel.lookup", return_value=model):
        yield Status.create("wasting", host)


def test_damage_ramps_with_each_application(session, wasting, host):
    for expected_hp in (150, 130, 100, 60, 10, 0):
        wasting.use(session, EffectPhase.PERFORM_STATUS)
        assert host.current_hp == expected_hp


def test_ramp_opens_at_a_single_dose(session, wasting, host):
    """
    The ramp has to start at 1x. It counts applications rather than turns
    precisely because the turn counter is already on 1 when a status is
    gained, which would open the ramp at double damage.
    """
    wasting.use(session, EffectPhase.PERFORM_STATUS)

    assert host.current_hp == 160 - 10


def test_ramp_needs_no_duration(session, wasting, host):
    """
    Lifecycle only counts turns for a status with a duration, so a ramp
    built on nr_turn would silently deal nothing at all here.
    """
    assert wasting.lifecycle.duration == 0

    wasting.use(session, EffectPhase.PERFORM_STATUS)

    assert host.current_hp < 160


def test_restacking_restarts_the_ramp(session, wasting, host):
    wasting.use(session, EffectPhase.PERFORM_STATUS)
    wasting.use(session, EffectPhase.PERFORM_STATUS)
    host.current_hp = 160

    wasting.stack()
    wasting.use(session, EffectPhase.PERFORM_STATUS)

    assert host.current_hp == 160 - 10


def test_other_phases_do_not_advance_the_ramp(session, wasting, host):
    wasting.use(session, EffectPhase.ON_START)
    wasting.use(session, EffectPhase.PERFORM_TECH)
    wasting.use(session, EffectPhase.PERFORM_STATUS)

    assert host.current_hp == 160 - 10


def test_fainted_host_is_left_alone(session, wasting, host):
    host.is_fainted = True

    result = wasting.use(session, EffectPhase.PERFORM_STATUS)

    assert not result.success
    assert host.current_hp == 160
