# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from tuxemon.npc_manager import NPCManager


@pytest.fixture
def npc_manager():
    return NPCManager()


@pytest.fixture
def session():
    s = MagicMock()
    s.player.slug = "player_slug"
    s.client.get_map_name.return_value = "map_a"
    return s


@pytest.fixture
def persistent_npcs(session):
    npc1 = MagicMock(
        slug="npc_1", instance_id=uuid4(), persistence=True, session=session
    )
    npc1.get_state.return_value = MagicMock(
        player_slug="npc_1", player_name="NPC One", current_map="map_a"
    )

    npc2 = MagicMock(
        slug="npc_2", instance_id=uuid4(), persistence=True, session=session
    )
    npc2.get_state.return_value = MagicMock(
        player_slug="npc_2", player_name="NPC Two", current_map="map_b"
    )

    return npc1, npc2


@pytest.mark.parametrize(
    "map_name, expected_location",
    [
        ("map_a", "npcs"),  # NPC on current map
        ("map_b", "npcs_off_map"),  # NPC off current map
    ],
)
@patch("tuxemon.npc_manager.NPC")
def test_load_persistent_npc_states(
    MockNPC, npc_manager, session, map_name, expected_location
):
    fake_npc = MagicMock(slug=f"npc_{expected_location}")
    MockNPC.return_value = fake_npc

    state = MagicMock(
        player_slug=f"npc_{expected_location}",
        player_name="NPC Test",
        current_map=map_name,
    )

    npc_manager.load_persistent_npc_states(session, [state])

    assert f"npc_{expected_location}" in getattr(
        npc_manager, expected_location
    )


def test_load_persistent_npc_states_skips_none_slug(npc_manager, session):
    state = MagicMock(
        player_slug=None, player_name="Nameless NPC", current_map="map_a"
    )
    npc_manager.load_persistent_npc_states(session, [state])
    assert npc_manager.npcs == {}
    assert npc_manager.npcs_off_map == {}


@patch("tuxemon.npc_manager.NPC")
def test_persistence_round_trip(
    MockNPC, npc_manager, session, persistent_npcs
):
    npc1, npc2 = persistent_npcs
    fake_npc1 = MagicMock(slug="npc_1")
    fake_npc2 = MagicMock(slug="npc_2")
    MockNPC.side_effect = [fake_npc1, fake_npc2]

    npc_manager.add_npc(npc1)
    npc_manager.add_npc_off_map(npc2)
    states = npc_manager.get_persistent_npc_states(session)
    assert len(states) == 2

    npc_manager.npcs.clear()
    npc_manager.npcs_off_map.clear()
    npc_manager.load_persistent_npc_states(session, states)

    assert "npc_1" in npc_manager.npcs
    assert "npc_2" in npc_manager.npcs_off_map
    assert "npc_1" not in npc_manager.npcs_off_map
    assert "npc_2" not in npc_manager.npcs
