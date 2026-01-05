# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock, patch

import pytest

from tuxemon.event.eventaction import ActionManager


@pytest.fixture
def action_manager():
    return ActionManager()


def test_init(action_manager):
    with patch("tuxemon.plugin.load_plugins", return_value={}):
        assert len(action_manager.actions) > 0


def test_get_action(action_manager):
    mock_action = MagicMock(return_value="add_monster")
    with patch(
        "tuxemon.plugin.load_plugins",
        return_value={"add_monster": mock_action},
    ):
        result = action_manager.get_action("add_monster", ["monster_slug", 1])
        assert result is not None


def test_get_action_not_implemented(action_manager):
    with patch("tuxemon.plugin.load_plugins", return_value={}):
        result = action_manager.get_action("action2")
        assert result is None


def test_get_action_with_type_error(action_manager):
    mock_action = MagicMock(side_effect=TypeError("Test error"))
    with patch(
        "tuxemon.plugin.load_plugins",
        return_value={"add_monster": mock_action},
    ):
        result = action_manager.get_action("add_monster", ["param1", "param2"])
        assert result is None


def test_get_actions(action_manager):
    with patch("tuxemon.plugin.load_plugins", return_value={}):
        actions = action_manager.get_actions()
        assert len(actions) > 0
