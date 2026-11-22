# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.event.conditions.char_at_teleport_faint import (
    CharAtTeleportFaintCondition,
)
from tuxemon.teleporter import TeleportFaint


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def character():
    character = MagicMock()
    character.teleport_faint = TeleportFaint("spyder_timber_cafe.tmx", 1, 10)
    return character


def test_char_on_recovery_map(session, character):
    character.current_map = "spyder_timber_cafe.tmx"
    session.client.get_npc.return_value = character

    assert CharAtTeleportFaintCondition("player").test(session) is True


def test_char_on_recovery_map_ignores_tile(session, character):
    """The whole map counts, not only the exact recovery tile."""
    character.current_map = "spyder_timber_cafe.tmx"
    character.tile_pos = (8, 4)
    session.client.get_npc.return_value = character

    assert CharAtTeleportFaintCondition("player").test(session) is True


def test_char_on_another_map(session, character):
    character.current_map = "spyder_route3.tmx"
    session.client.get_npc.return_value = character

    assert CharAtTeleportFaintCondition("player").test(session) is False


def test_char_not_found(session):
    session.client.get_npc.return_value = None

    assert CharAtTeleportFaintCondition("player").test(session) is False
