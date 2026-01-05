# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.event.eventaction import ActionContextManager
from tuxemon.session import Session


@pytest.fixture
def mock_action():
    action = MagicMock()
    action.cancelled = False
    return action


@pytest.fixture
def mock_session():
    return MagicMock(spec=Session)


def test_context_manager_enter(mock_action, mock_session):
    with ActionContextManager(mock_action, mock_session):
        mock_action.on_start.assert_called_once()


def test_context_manager_exit(mock_action, mock_session):
    with ActionContextManager(mock_action, mock_session):
        pass
    mock_action.cleanup.assert_called_once()


def test_cancelled_action(mock_action, mock_session):
    mock_action.cancelled = True
    with ActionContextManager(mock_action, mock_session):
        mock_action.start.assert_not_called()
    mock_action.cleanup.assert_not_called()


def test_exception_handling(mock_action, mock_session):
    mock_action.cleanup = MagicMock(side_effect=Exception("Cleanup error"))
    with pytest.raises(Exception):
        with ActionContextManager(mock_action, mock_session):
            pass
