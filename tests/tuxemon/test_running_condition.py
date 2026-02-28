# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.db import BoundingBox, Operator, SpatialCondition
from tuxemon.event.eventcondition import ConditionManager
from tuxemon.event.running import (
    ConditionEvaluator,
    ConditionState,
    RunningCondition,
)
from tuxemon.session import Session


@pytest.fixture
def mock_condition():
    cond = MagicMock()
    cond.name = "TestCondition"
    cond.test.return_value = True
    cond.is_expected = True
    return cond


@pytest.fixture
def mock_condition_manager(mock_condition):
    mgr = MagicMock(spec=ConditionManager)
    mgr.get_condition.return_value = mock_condition
    return mgr


@pytest.fixture
def mock_session():
    return MagicMock(spec=Session)


@pytest.fixture
def spatial_condition():
    box = BoundingBox(x=0, y=0, width=1, height=1)
    return SpatialCondition(
        type="test_type",
        parameters=[],
        box=box,
        operator=Operator.IS,
        name="TestCondition",
    )


@pytest.fixture
def evaluator(mock_session, mock_condition_manager):
    return ConditionEvaluator(
        session=mock_session,
        condition_manager=mock_condition_manager,
    )


@pytest.fixture
def running_condition(spatial_condition, evaluator):
    return RunningCondition(spatial_condition, evaluator)


def test_initial_state(running_condition):
    assert running_condition.state == ConditionState.WAITING
    assert running_condition.result is None


def test_start_check_sets_state_to_checking(running_condition):
    running_condition.start_check()
    assert running_condition.state == ConditionState.CHECKING


def test_cancel_sets_state_to_cancelled(running_condition):
    running_condition.cancel()
    assert running_condition.is_cancelled()
    assert running_condition.state == ConditionState.CANCELLED


def test_check_condition_met(running_condition):
    result = running_condition.check()
    assert result is True
    assert running_condition.is_met()
    assert running_condition.result is True


def test_check_condition_failed(running_condition, mock_condition):
    mock_condition.test.return_value = False
    result = running_condition.check()
    assert result is False
    assert running_condition.is_failed()
    assert running_condition.result is False


def test_check_condition_type_not_found(
    running_condition, mock_condition_manager
):
    mock_condition_manager.get_condition.return_value = None
    result = running_condition.check()
    assert result is False
    assert running_condition.is_failed()
    assert running_condition.result is False


def test_check_condition_exception(running_condition, mock_condition):
    mock_condition.test.side_effect = Exception("Test error")
    result = running_condition.check()
    assert result is False
    assert running_condition.is_failed()
    assert running_condition.result is False


def test_check_cancelled_condition(running_condition):
    running_condition.cancel()
    result = running_condition.check()
    assert result is False
    assert running_condition.is_cancelled()
    assert running_condition.result is False


def test_state_flag_helpers(running_condition):
    running_condition.state = ConditionState.MET
    assert running_condition.is_met()

    running_condition.state = ConditionState.FAILED
    assert running_condition.is_failed()

    running_condition.state = ConditionState.CANCELLED
    assert running_condition.is_cancelled()
