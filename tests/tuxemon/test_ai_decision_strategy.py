# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock, patch

import pytest

from tuxemon.ai.ai import (
    AIConfigLoader,
    AIItems,
    ItemEntry,
    TrainerAIDecisionStrategy,
    WildAIDecisionStrategy,
)


@pytest.fixture
def mock_ai():
    ai = MagicMock()
    ai.character.slug = "trainer1"
    ai.character.items = []
    ai.opponents = [MagicMock(slug="enemy")]
    ai.monster.slug = "monster1"
    return ai


@pytest.fixture
def mock_tracker():
    tracker = MagicMock()
    tracker.get_valid_moves.return_value = [
        (MagicMock(slug="tackle"), MagicMock(slug="enemy"))
    ]
    tracker.evaluate_technique.return_value = 1.0
    return tracker


@pytest.fixture
def mock_evaluator():
    evaluator = MagicMock()
    evaluator.get_best_target.return_value = MagicMock(slug="enemy")
    return evaluator


# TrainerAIDecisionStrategy tests
def test_make_decision_use_potion(mock_ai, mock_evaluator, mock_tracker):
    mock_item = MagicMock(slug="potion")
    mock_ai.character.items = [mock_item]
    mock_ai.character.bag = MagicMock()
    mock_ai.character.bag._items = [mock_item]
    mock_ai.monster.hp_ratio = 0.40

    with patch.object(
        AIConfigLoader,
        "get_ai_items",
        return_value=AIItems(items={"potion": ItemEntry(hp_range=(0.2, 0.8))}),
    ):
        strategy = TrainerAIDecisionStrategy(
            mock_evaluator,
            mock_tracker,
            MagicMock(),
            AIItems(items={"potion": ItemEntry(hp_range=(0.2, 0.8))}),
            MagicMock(),
        )
        strategy.make_decision(mock_ai)

    mock_ai.action_item.assert_called_once_with(mock_item)


def test_make_decision_select_move(mock_ai, mock_evaluator, mock_tracker):
    mock_tracker.get_valid_moves.return_value = [
        (MagicMock(slug="tackle"), MagicMock(slug="enemy"))
    ]
    mock_tracker.evaluate_technique.return_value = 10.0

    strategy = TrainerAIDecisionStrategy(
        mock_evaluator, mock_tracker, MagicMock(), MagicMock(), MagicMock()
    )
    strategy.make_decision(mock_ai)

    mock_tracker.get_valid_moves.assert_called_once_with(mock_ai.opponents)
    mock_ai.action_tech.assert_called_once()


def test_select_move_no_valid_actions(mock_ai, mock_evaluator, mock_tracker):
    mock_tracker.get_valid_moves.return_value = []
    target = MagicMock(slug="enemy")

    strategy = TrainerAIDecisionStrategy(
        mock_evaluator, mock_tracker, MagicMock(), MagicMock(), MagicMock()
    )

    with patch(
        "tuxemon.technique.technique.Technique.create",
        return_value=MagicMock(slug="skip"),
    ):
        technique, chosen_target = strategy.select_move(mock_ai, target)

    assert technique.slug == "skip"
    assert chosen_target == target


def test_handle_monster_config_executes_technique(
    mock_ai, mock_evaluator, mock_tracker
):
    technique = MagicMock(slug="fireball")
    opponent = MagicMock(slug="enemy")
    mock_tracker.get_valid_moves.return_value = [(technique, opponent)]

    monster_config = MagicMock()
    monster_config.techniques = [
        MagicMock(technique="fireball", condition=None)
    ]

    strategy = TrainerAIDecisionStrategy(
        mock_evaluator, mock_tracker, MagicMock(), MagicMock(), MagicMock()
    )
    result = strategy.handle_monster_config(mock_ai, monster_config)

    assert result is True
    mock_ai.action_tech.assert_called_once_with(technique, opponent)


def test_need_healing_returns_false_for_unknown_item(
    mock_ai, mock_evaluator, mock_tracker
):
    item = MagicMock(slug="unknown")
    ai_items = MagicMock()
    ai_items.items = {}  # no entry

    strategy = TrainerAIDecisionStrategy(
        mock_evaluator, mock_tracker, MagicMock(), ai_items, MagicMock()
    )
    assert strategy.need_healing(mock_ai, item) is False


def test_check_ai_techs_returns_correct_config(mock_evaluator, mock_tracker):
    ai_techs = MagicMock()
    ai_techs.techniques = {
        "wildslug": "wildconfig",
        "trainer_slug": "trainerconfig",
    }

    wild_monster = MagicMock(slug="wildslug", wild=True)
    trainer_monster = MagicMock(slug="trainer_slug", wild=False)
    trainer_monster.get_owner.return_value = MagicMock(slug="trainer_slug")

    strategy = TrainerAIDecisionStrategy(
        mock_evaluator, mock_tracker, MagicMock(), MagicMock(), ai_techs
    )

    assert strategy.check_ai_techs(wild_monster) == "wildconfig"
    assert strategy.check_ai_techs(trainer_monster) == "trainerconfig"


# WildAIDecisionStrategy tests
def test_wild_ai_make_decision(mock_ai, mock_evaluator, mock_tracker):
    mock_tracker.get_valid_moves.return_value = [
        (MagicMock(slug="scratch"), MagicMock(slug="enemy"))
    ]
    mock_tracker.evaluate_technique.return_value = 5.0
    mock_evaluator.get_best_target.return_value = MagicMock(slug="enemy")

    mock_trainers = MagicMock()
    mock_items = MagicMock()
    mock_techs = MagicMock()

    strategy = WildAIDecisionStrategy(
        mock_evaluator,
        mock_tracker,
        mock_trainers,
        mock_items,
        mock_techs,
    )

    strategy.make_decision(mock_ai)
    mock_ai.action_tech.assert_called_once()
