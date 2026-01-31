# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pytest

from tuxemon.db import GameCondition
from tuxemon.game_variables import GameVariablesManager


@pytest.fixture
def manager():
    return GameVariablesManager(
        initial_player={"hp": 10, "daytime": True},
        initial_world={"weather": "rain", "difficulty": 2},
    )


def test_scope_basic_operations(manager):
    assert manager.player.get("hp") == 10
    assert manager.world.get("weather") == "rain"

    manager.player.set("hp", 20)
    assert manager.player.get("hp") == 20

    assert manager.player.has("hp")
    assert not manager.player.has("missing")

    assert manager.world.remove("weather")
    assert not manager.world.has("weather")


def test_dirty_flags(manager):
    assert not manager.is_any_dirty()

    manager.player.set("hp", 99)
    assert manager.is_any_dirty()

    manager.clear_all_dirty()
    assert not manager.is_any_dirty()

    manager.world.set("difficulty", 5)
    assert manager.is_any_dirty()


@pytest.mark.parametrize(
    "key, expected",
    [
        ("hp", 10),  # player
        ("daytime", True),  # player
        ("weather", "rain"),  # world
        ("difficulty", 2),  # world
        ("missing", None),  # not found anywhere
    ],
)
def test_resolve_value(manager, key, expected):
    assert manager._resolve_value(key) == expected


@pytest.mark.parametrize(
    "conditions, expected",
    [
        ([{"hp": 10}], True),
        ([{"hp": 5}], False),
        ([{"weather": "rain"}], True),
        ([{"weather": "sun"}], False),
        ([{"hp": 10}, {"weather": "rain"}], True),
        ([{"hp": 10}, {"weather": "sun"}], False),
        ([], True),  # empty = always true
    ],
)
def test_check_logic_dict(manager, conditions, expected):
    assert manager.check_logic(conditions) is expected


@pytest.mark.parametrize(
    "conditions, expected",
    [
        ([GameCondition(key="hp", value=10)], True),
        ([GameCondition(key="hp", value=5)], False),
        ([GameCondition(key="weather", value="rain")], True),
        ([GameCondition(key="weather", value="sun")], False),
        (
            [
                GameCondition(key="hp", value=10),
                GameCondition(key="weather", value="rain"),
            ],
            True,
        ),
        (
            [
                GameCondition(key="hp", value=10),
                GameCondition(key="weather", value="sun"),
            ],
            False,
        ),
        ([], True),
    ],
)
def test_check_conditions(manager, conditions, expected):
    assert manager.check_conditions(conditions) is expected


@pytest.mark.parametrize(
    "cond, expected",
    [
        (GameCondition(key="hp", value=10, scope="player"), True),
        (GameCondition(key="hp", value=10, scope="world"), False),
        (GameCondition(key="weather", value="rain", scope="world"), True),
        (GameCondition(key="weather", value="rain", scope="player"), False),
    ],
)
def test_check_conditions_scope(manager, cond, expected):
    assert manager.check_conditions([cond]) is expected


def test_missing_requirements(manager):
    conditions = [
        GameCondition(key="hp", value=10, description="HP must be 10"),
        GameCondition(key="weather", value="sun", description="Sunny weather"),
        GameCondition(key="difficulty", value=2),
    ]

    missing = manager.get_missing_requirements(conditions)

    assert "Sunny weather" in missing
    assert "Missing requirement: difficulty" not in missing
    assert len(missing) == 1


def test_missing_requirements_empty(manager):
    assert manager.get_missing_requirements([]) == []


def test_check_logic_unknown_key(manager):
    assert not manager.check_logic([{"unknown": 5}])


def test_check_conditions_unknown_key(manager):
    cond = GameCondition(key="unknown", value=123)
    assert not manager.check_conditions([cond])


def test_numeric_comparison(manager):
    manager.player.set("score", 100)
    cond = GameCondition(key="score", value=100)
    assert manager.check_conditions([cond])


def test_none_values(manager):
    manager.player.set("flag", None)
    cond = GameCondition(key="flag", value=None)
    assert manager.check_conditions([cond])
