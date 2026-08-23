# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from tuxemon.core.effects.wasting import WastingEffect
from tuxemon.db import EffectPhase
from tuxemon.status.lifecycle import Lifecycle

WASTING_DB = (
    Path(__file__).resolve().parents[2]
    / "mods"
    / "tuxemon"
    / "db"
    / "status"
    / "wasting.yaml"
)


@pytest.fixture
def host():
    monster = MagicMock()
    monster.hp = 160
    monster.current_hp = 160
    monster.is_fainted = False
    return monster


def wasting_status(host, nr_turn):
    status = MagicMock()
    status.host = host
    status.name = "Wasting"
    status.nr_turn = nr_turn
    status.has_phase.side_effect = lambda phase: (
        phase == EffectPhase.PERFORM_STATUS
    )
    return status


@pytest.mark.parametrize(
    "nr_turn, expected_damage",
    [
        pytest.param(1, 10, id="first_turn"),
        pytest.param(2, 20, id="second_turn"),
        pytest.param(3, 30, id="third_turn"),
    ],
)
def test_damage_ramps_with_the_turn_counter(host, nr_turn, expected_damage):
    result = WastingEffect(divisor=16).apply_status(
        MagicMock(), wasting_status(host, nr_turn)
    )

    assert result.success
    assert host.current_hp == 160 - expected_damage


def test_ramp_opens_at_double_the_base_damage():
    """
    Gaining a status ticks it to turn 1 and the end of that same round ticks
    it again, so the first damage a monster actually takes is 2x the base.
    """
    lifecycle = Lifecycle(duration=100)

    lifecycle.tick_turn()  # gained
    lifecycle.tick_turn()  # end of the round it was gained on

    assert lifecycle.turn == 2


def test_wasting_has_a_duration_so_its_counter_advances():
    """
    ``Lifecycle.tick_turn`` is a no-op while duration is 0, which would pin
    ``nr_turn`` at 0 and make the ramping damage above always zero.
    """
    data = yaml.safe_load(WASTING_DB.read_text(encoding="utf-8"))

    assert data["duration"] > 0
