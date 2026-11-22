# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Guards the faint recovery flow scripted in the spyder scenario.

Fainting used to replay "You should heal your monsters before heading off"
because the teleport event stayed satisfied once the player landed on their
recovery map, and the healing rode along on that second firing.
"""

from pathlib import Path

import pytest

from tuxemon.constants.asset_loader import fetch_asset
from tuxemon.database.runtime import db  # noqa: F401  # side-effect import
from tuxemon.database.yaml_utils import load_yaml

SCENARIO = "spyder.yaml"
REMINDER = "translated_dialog heal_before_leave"
HEAL = "set_monster_health"


@pytest.fixture(scope="module")
def events():
    return load_yaml(Path(fetch_asset("maps", SCENARIO)))["events"]


def test_teleport_faint_stops_at_the_recovery_point(events):
    """Without this guard the event fires again on arrival."""
    conditions = events["Teleport Faint"]["conditions"]

    assert "not char_at_teleport_faint player" in conditions


def test_teleport_faint_only_teleports(events):
    """Healing and the reminder belong to the arrival events."""
    actions = events["Teleport Faint"]["actions"]

    assert "teleport_faint player,false" in actions
    assert REMINDER not in actions
    assert HEAL not in actions


def test_recovery_heals_outside_clinics(events):
    event = events["Recover After Faint"]

    assert HEAL in event["actions"]
    assert "set_monster_status" in event["actions"]
    assert "is char_at_teleport_faint player" in event["conditions"]
    assert "not location_type clinic" in event["conditions"]


def test_clinics_charge_instead_of_healing(events):
    """A clinic recovery leaves the party fainted for the nurse to bill."""
    clinic = events["Fainted At Clinic"]

    assert HEAL not in clinic["actions"]
    assert REMINDER in clinic["actions"]
    assert "is location_type clinic" in clinic["conditions"]


def test_clinic_reminder_shows_once(events):
    """The party stays fainted, so only a variable can end the repeat."""
    clinic = events["Fainted At Clinic"]

    assert "is variable_set faint_recovery:pending" in clinic["conditions"]
    assert "set_variable faint_recovery:null" in clinic["actions"]
    teleport = events["Teleport Faint"]["actions"]
    assert "set_variable faint_recovery:pending" in teleport


def test_no_event_heals_and_asks_for_healing(events):
    """The reminder contradicts itself when it follows a heal."""
    for name, event in events.items():
        actions = event.get("actions", [])
        assert not (REMINDER in actions and HEAL in actions), (
            f"'{name}' heals the party and then tells it to go and heal."
        )
