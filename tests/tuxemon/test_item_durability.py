# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import random

import pytest

from tuxemon.db import ItemBehaviors
from tuxemon.item.durability import Durability
from tuxemon.item.item import Item


@pytest.mark.parametrize(
    "max_wear, expected",
    [
        (0, False),
        (1, True),
        (10, True),
    ],
)
def test_has_wear(max_wear, expected):
    d = Durability(max_wear=max_wear)
    assert d.has_wear == expected


@pytest.mark.parametrize(
    "max_wear, current, expected",
    [
        (0, 0, False),  # no wear system
        (5, 0, False),
        (5, 4, False),
        (5, 5, True),
        (5, 10, True),
    ],
)
def test_is_broken(max_wear, current, expected):
    d = Durability(max_wear=max_wear, current=current)
    assert d.is_broken == expected


@pytest.mark.parametrize(
    "max_wear, current, expected",
    [
        (0, 0, 0.0),
        (10, 0, 0.0),
        (10, 5, 0.5),
        (10, 10, 1.0),
        (10, 20, 1.0),  # clamped
        (10, -5, 0.0),  # clamped
    ],
)
def test_ratio(max_wear, current, expected):
    d = Durability(max_wear=max_wear, current=current)
    assert d.ratio == expected


@pytest.mark.parametrize(
    "max_wear, current, amount, expected_current, expected_broke",
    [
        (0, 0, 1, 0, False),  # no wear system
        (5, 0, 1, 1, False),
        (5, 4, 1, 5, True),  # breaks on reaching max
        (5, 4, 10, 5, True),  # clamped
        (5, 5, 1, 5, True),  # already broken
    ],
)
def test_increase_no_random(
    max_wear, current, amount, expected_current, expected_broke
):
    d = Durability(max_wear=max_wear, current=current, break_chance=0.0)
    broke = d.increase(amount)
    assert d.current == expected_current
    assert broke == expected_broke


def test_increase_random_break():
    d = Durability(max_wear=10, current=1, break_chance=1.0)
    broke = d.increase(1)
    assert broke is True
    assert d.current == d.max_wear


@pytest.mark.parametrize(
    "break_chance, random_value, expected",
    [
        (0.0, 0.0, False),
        (0.5, 0.6, False),
        (0.5, 0.4, True),
        (1.0, 0.999, True),
    ],
)
def test_should_break(monkeypatch, break_chance, random_value, expected):
    monkeypatch.setattr(random, "random", lambda: random_value)
    d = Durability(max_wear=5, break_chance=break_chance)
    assert d.should_break() == expected


def test_reset():
    d = Durability(max_wear=10, current=7)
    d.reset()
    assert d.current == 0


@pytest.mark.parametrize(
    "current, amount, expected",
    [
        (5, -1, 0),  # full repair
        (5, 0, 5),
        (5, 2, 3),
        (5, 10, 0),  # clamped
    ],
)
def test_repair(current, amount, expected):
    d = Durability(max_wear=10, current=current)
    d.repair(amount)
    assert d.current == expected


def test_try_increase_no_wear():
    d = Durability(max_wear=0, current=0)
    assert d.try_increase(1) is False
    assert d.current == 0


def test_try_increase_negative_amount():
    d = Durability(max_wear=5, current=2)
    assert d.try_increase(-1) is False
    assert d.current == 2


def test_try_increase_valid():
    d = Durability(max_wear=5, current=2)
    broke = d.try_increase(2)
    assert broke is False
    assert d.current == 4


def test_try_increase_breaks():
    d = Durability(max_wear=5, current=4, break_chance=0.0)
    broke = d.try_increase(1)
    assert broke is True
    assert d.current == 5


def test_try_reset_no_wear():
    d = Durability(max_wear=0, current=5)
    d.try_reset()
    assert d.current == 5


def test_try_reset_with_wear():
    d = Durability(max_wear=10, current=7)
    d.try_reset()
    assert d.current == 0


def test_try_repair_no_wear():
    d = Durability(max_wear=0, current=5)
    d.try_repair(3)
    assert d.current == 5


@pytest.mark.parametrize(
    "current, amount, expected",
    [
        (5, -1, 0),  # full repair
        (5, 0, 5),
        (5, 2, 3),
        (5, 10, 0),
    ],
)
def test_try_repair_with_wear(current, amount, expected):
    d = Durability(max_wear=10, current=current)
    d.try_repair(amount)
    assert d.current == expected


def test_try_increase_calls_increase(monkeypatch):
    d = Durability(max_wear=5, current=1)

    called = {"value": False}

    def fake_increase(amount):
        called["value"] = True
        return True

    monkeypatch.setattr(d, "increase", fake_increase)
    d.try_increase(1)

    assert called["value"] is True


def test_try_reset_calls_reset(monkeypatch):
    d = Durability(max_wear=5, current=3)

    called = {"value": False}

    def fake_reset():
        called["value"] = True

    monkeypatch.setattr(d, "reset", fake_reset)

    d.try_reset()

    assert called["value"] is True


def test_try_repair_calls_repair(monkeypatch):
    d = Durability(max_wear=5, current=3)

    called = {"value": False}

    def fake_repair(amount):
        called["value"] = True

    monkeypatch.setattr(d, "repair", fake_repair)

    d.try_repair(2)

    assert called["value"] is True
