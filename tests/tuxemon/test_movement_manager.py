# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.camera.camera import CameraManager
from tuxemon.client import LocalPygameClient
from tuxemon.db import Direction
from tuxemon.event.eventmanager import EventManager
from tuxemon.movement import MovementManager
from tuxemon.npc import NPC
from tuxemon.platform.const import intentions
from tuxemon.platform.input_manager import InputManager


@pytest.fixture
def mock_client():
    client = MagicMock(spec=LocalPygameClient)
    client.event_manager = MagicMock(spec=EventManager)
    client.input_manager = MagicMock(spec=InputManager)
    client.camera_manager = MagicMock(spec=CameraManager)
    return client


@pytest.fixture
def movement_manager(mock_client):
    return MovementManager(
        mock_client.event_manager,
        mock_client.input_manager,
        mock_client.camera_manager,
    )


@pytest.fixture
def mock_npc():
    npc = MagicMock(spec=NPC)
    npc.slug = "npc_1"
    npc.mover = MagicMock()
    return npc


def test_move_char(movement_manager, mock_npc):
    movement_manager.move_char(mock_npc, Direction.up)
    mock_npc.set_move_direction.assert_called_with(Direction.up)


def test_stop_char(movement_manager, mock_npc, mock_client):
    movement_manager.wants_to_move_char["npc_1"] = Direction.up

    movement_manager.stop_char(mock_npc)

    assert "npc_1" not in movement_manager.wants_to_move_char
    mock_client.event_manager.release_controls.assert_called_once()
    mock_npc.cancel_movement.assert_called_once()


def test_unlock_controls(movement_manager, mock_npc):
    movement_manager.wants_to_move_char["npc_1"] = Direction.down

    movement_manager.unlock_controls(mock_npc)

    assert "npc_1" in movement_manager.allow_char_movement
    mock_npc.set_move_direction.assert_called_with(Direction.down)


def test_lock_controls(movement_manager, mock_npc):
    movement_manager.allow_char_movement.add("npc_1")

    movement_manager.lock_controls(mock_npc)

    assert "npc_1" not in movement_manager.allow_char_movement


def test_stop_and_reset_char(movement_manager, mock_npc, mock_client):
    movement_manager.wants_to_move_char["npc_1"] = Direction.left

    movement_manager.stop_and_reset_char(mock_npc)

    assert "npc_1" not in movement_manager.wants_to_move_char
    mock_client.event_manager.release_controls.assert_called_once()
    mock_npc.abort_movement.assert_called_once()


@pytest.mark.parametrize(
    "allowed, expected",
    [
        (True, True),
        (False, False),
    ],
)
def test_is_movement_allowed(movement_manager, mock_npc, allowed, expected):
    if allowed:
        movement_manager.allow_char_movement.add("npc_1")

    assert movement_manager.is_movement_allowed(mock_npc) is expected


def test_has_pending_movement(movement_manager, mock_npc):
    assert not movement_manager.has_pending_movement(mock_npc)

    movement_manager.wants_to_move_char["npc_1"] = Direction.up
    assert movement_manager.has_pending_movement(mock_npc)

    del movement_manager.wants_to_move_char["npc_1"]
    assert not movement_manager.has_pending_movement(mock_npc)


def test_handle_directional_input_valid_and_allowed(
    movement_manager, mock_npc, mock_client
):
    mock_camera = MagicMock()
    mock_camera.is_following.return_value = True
    mock_client.camera_manager.get_active_camera.return_value = mock_camera

    movement_manager.allow_char_movement.add("npc_1")

    event = MagicMock()
    event.button = next(iter(movement_manager.direction_map))
    event.held = True
    event.pressed = True

    result = movement_manager.handle_directional_input(mock_npc, event)

    assert result is None
    mock_npc.set_move_direction.assert_called_once()


def test_handle_directional_input_valid_but_not_allowed(
    movement_manager, mock_npc, mock_client
):
    mock_camera = MagicMock()
    mock_camera.is_following.return_value = True
    mock_client.camera_manager.get_active_camera.return_value = mock_camera

    event = MagicMock()
    event.button = next(iter(movement_manager.direction_map))
    event.held = True
    event.pressed = True

    result = movement_manager.handle_directional_input(mock_npc, event)

    assert result is None
    mock_npc.set_move_direction.assert_not_called()


def test_handle_directional_input_camera_not_following(
    movement_manager, mock_npc, mock_client
):
    mock_camera = MagicMock()
    mock_camera.is_following.return_value = False
    mock_client.camera_manager.get_active_camera.return_value = mock_camera

    event = MagicMock()
    event.button = next(iter(movement_manager.direction_map))
    event.held = True
    event.pressed = True

    movement_manager.handle_directional_input(mock_npc, event)

    mock_client.camera_manager.handle_input.assert_called_with(event)


def test_handle_directional_input_release(
    movement_manager, mock_npc, mock_client
):
    mock_camera = MagicMock()
    mock_camera.is_following.return_value = True
    mock_client.camera_manager.get_active_camera.return_value = mock_camera

    movement_manager.wants_to_move_char["npc_1"] = Direction.down

    event = MagicMock()
    event.button = intentions.DOWN
    event.held = False
    event.pressed = False

    result = movement_manager.handle_directional_input(mock_npc, event)

    assert result is None
    mock_npc.cancel_movement.assert_called_once()


def test_handle_directional_input_invalid_button(movement_manager, mock_npc):
    event = MagicMock()
    event.button = 9999
    event.held = True
    event.pressed = True

    result = movement_manager.handle_directional_input(mock_npc, event)

    assert result == event
