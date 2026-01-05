# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock, patch

import pytest

from tuxemon.db import SpatialCondition
from tuxemon.event.eventcondition import ConditionManager, EventCondition
from tuxemon.event.running import ConditionEvaluator


@pytest.fixture
def mock_load_plugins():
    with patch("tuxemon.plugin.load_plugins") as mock:
        yield mock


@pytest.fixture
def condition_manager(mock_load_plugins):
    mock_condition_class = MagicMock()
    mock_load_plugins.return_value = {"char_at": mock_condition_class}
    manager = ConditionManager()
    manager._mock_condition_class = mock_condition_class
    return manager


def test_get_condition_found(condition_manager):
    mock_cond_data = MagicMock(spec=SpatialCondition)
    mock_cond_data.type = "char_at"
    mock_cond_data.operator = "is"
    condition = condition_manager.get_condition(mock_cond_data)
    assert condition is not None
    assert condition.is_expected is True


def test_get_condition_not_found(condition_manager):
    mock_cond_data = MagicMock(spec=SpatialCondition)
    mock_cond_data.type = "nonexistent"
    mock_cond_data.operator = "is"
    condition = condition_manager.get_condition(mock_cond_data)
    assert condition is None


def test_get_condition_with_parameters(condition_manager):
    mock_cond_data = MagicMock()
    mock_cond_data.type = "char_at"
    mock_cond_data.operator = "is"
    mock_cond_data.parameters = ["hero", 0, "H"]
    condition_manager._mock_condition_class.return_value = MagicMock()
    condition = condition_manager.get_condition(mock_cond_data)
    assert condition is not None
    assert condition.is_expected is True


def test_get_conditions_are_event_conditions(condition_manager):
    conditions = condition_manager.get_conditions()

    for cond_class in conditions:
        assert issubclass(cond_class, EventCondition)


@pytest.fixture
def evaluator():
    mock_session = MagicMock()
    mock_condition = MagicMock()
    mock_condition.test.return_value = True
    mock_condition.is_expected = True
    mock_condition_manager = MagicMock()
    mock_condition_manager.get_condition.return_value = mock_condition
    return ConditionEvaluator(
        session=mock_session,
        condition_manager=mock_condition_manager,
    )


def test_evaluate_condition_met(evaluator):
    result = evaluator.evaluate(MagicMock())
    assert result is True


def test_evaluate_condition_failed(evaluator):
    evaluator.condition_manager.get_condition.return_value.test.return_value = (
        False
    )
    result = evaluator.evaluate(MagicMock())
    assert result is False


def test_evaluate_condition_not_found(evaluator):
    evaluator.condition_manager.get_condition.return_value = None
    with pytest.raises(ValueError):
        evaluator.evaluate(MagicMock())
