# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pytest
from unittest.mock import MagicMock
from tuxemon.network.client import TuxemonClient

@pytest.fixture
def client():
    """Provides a fresh TuxemonClient with a mocked game for each test."""
    game = MagicMock()
    return TuxemonClient(game)

def test_connect_and_disconnect(client):
    client.connect_to_host("127.0.0.1", 40081)
    assert client.listening
    assert client.selected_game == ("127.0.0.1", 40081)

    client.disconnect()
    assert not client.listening
    assert client.selected_game is None
    assert client.server_list == []
    assert client.client.registry == {}

def test_disconnect_when_not_listening(client):
    client.listening = False
    client.disconnect() 
    assert client.listening is False
    assert client.selected_game is None

def test_registry_property(client):
    client.client.registry = {"abc": {"sprite": "dummy"}}
    assert client.registry == {"abc": {"sprite": "dummy"}}

def test_update_calls_connection_manager_and_dispatcher(client):
    client.connection_manager.update = MagicMock()
    client.client.get_incoming_events = MagicMock(return_value=[{"type": "PING"}])
    client.dispatcher.dispatch = MagicMock()

    client.update(0.1)

    client.connection_manager.update.assert_called_once_with(0.1)
    client.dispatcher.dispatch.assert_called_once_with({"type": "PING"})

def test_check_notify_dispatches_multiple_events(client):
    client.client.get_incoming_events = MagicMock(
        return_value=[{"type": "PING"}, {"type": "MOVE"}]
    )
    client.dispatcher.dispatch = MagicMock()
    client.check_notify()
    assert client.dispatcher.dispatch.call_count == 2

def test_update_multiplayer_list_delegates(client):
    client.discovery.update_multiplayer_list = MagicMock()
    client.update_multiplayer_list()
    client.discovery.update_multiplayer_list.assert_called_once()

def test_populate_player_delegates(client):
    client.sync_manager.populate_player = MagicMock()
    client.populate_player("PUSH_SELF")
    client.sync_manager.populate_player.assert_called_once_with("PUSH_SELF")

def test_update_player_delegates(client):
    client.sync_manager.update_player = MagicMock()
    client.update_player("north", "CLIENT_MAP_UPDATE")
    client.sync_manager.update_player.assert_called_once_with("north", "CLIENT_MAP_UPDATE")

def test_set_key_condition_delegates(client):
    client.input_translator.translate = MagicMock()
    fake_event = {"key": "up"}
    client.set_key_condition(fake_event)
    client.input_translator.translate.assert_called_once_with(fake_event)

def test_player_interact_delegates(client):
    client.interaction_manager.player_interact = MagicMock()
    sprite = MagicMock()
    client.player_interact(sprite, "talk", "CLIENT_INTERACTION", response="hello")
    client.interaction_manager.player_interact.assert_called_once_with(
        sprite, "talk", "CLIENT_INTERACTION", "hello"
    )

def test_route_combat_delegates(client):
    client.interaction_manager.route_combat = MagicMock()
    event = {"combat": True}
    client.route_combat(event)
    client.interaction_manager.route_combat.assert_called_once_with(event)

def test_send_ping_delegates(client):
    client.sync_manager.send_ping = MagicMock()
    client.send_ping()
    client.sync_manager.send_ping.assert_called_once()

def test_update_client_map_updates_registry(client):
    sprite = MagicMock()
    client.client.registry["abc"] = {"sprite": sprite}
    event_data = MagicMock()
    event_data.map_name = "forest"
    event_data.char_dict = {"hp": 100}

    import tuxemon.network.client as client_module
    client_module.update_client = MagicMock()

    client.update_client_map("abc", event_data)

    assert client.client.registry["abc"]["map_name"] == "forest"
    client_module.update_client.assert_called_once_with(sprite, {"hp": 100}, client.game)
