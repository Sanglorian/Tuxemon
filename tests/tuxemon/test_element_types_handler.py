# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pytest

from tuxemon.db import ElementModel
from tuxemon.database.bootstrap import db
from tuxemon.element import Element, ElementTypesHandler


@pytest.fixture
def elements():
    fire = ElementModel(
        slug="fire", icon="gfx/ui/icons/element/fire_type.png", types=[]
    )
    metal = ElementModel(
        slug="metal", icon="gfx/ui/icons/element/metal_type.png", types=[]
    )
    aether = ElementModel(
        slug="aether", icon="gfx/ui/icons/element/aether_type.png", types=[]
    )

    db.database["element"] = {
        "fire": fire,
        "metal": metal,
        "aether": aether,
    }

    return {
        "fire": Element("fire"),
        "metal": Element("metal"),
        "aether": Element("aether"),
    }


@pytest.fixture
def handler(elements):
    return ElementTypesHandler(["metal", "fire"])


def test_init_with_no_types():
    basic = ElementTypesHandler()
    assert basic.current == []
    assert basic.default == []


def test_init_with_types(handler):
    assert len(handler.current) == 2
    assert len(handler.default) == 2


def test_set_types(elements):
    basic = ElementTypesHandler()
    basic.set_types([elements["fire"], elements["metal"]])
    assert len(basic.current) == 2


def test_reset_to_default(handler):
    new_element = Element("metal")
    handler.set_types([new_element])
    handler.reset_to_default()
    assert len(handler.current) == 2


def test_get_type_slugs(handler):
    assert handler.get_type_slugs() == ["metal", "fire"]


def test_has_type(handler):
    assert handler.has_type("metal")
    assert not handler.has_type("non_existent_type")


def test_primary_type(handler):
    assert handler.primary.slug == "metal"
    assert handler.primary is not None


@pytest.mark.parametrize(
    "attackers, defenders, expected_fn",
    [
        (["fire"], ["metal"], lambda e: e["fire"].lookup_multiplier("metal")),
        (["metal"], ["fire"], lambda e: e["metal"].lookup_multiplier("fire")),
        (
            ["fire", "metal"],
            ["fire", "metal"],
            lambda e: (
                e["fire"].lookup_multiplier("fire")
                * e["fire"].lookup_multiplier("metal")
                * e["metal"].lookup_multiplier("fire")
                * e["metal"].lookup_multiplier("metal")
            ),
        ),
        (
            ["fire", "aether"],
            ["metal"],
            lambda e: e["fire"].lookup_multiplier("metal"),
        ),
    ],
)
def test_calculate_affinity_score(elements, attackers, defenders, expected_fn):
    atk = [elements[a] for a in attackers]
    dfn = [elements[d] for d in defenders]
    score = ElementTypesHandler.calculate_affinity_score(atk, dfn)
    assert score == expected_fn(elements)


@pytest.mark.parametrize(
    "defenders, attacker, expected_fn",
    [
        (["metal"], "fire", lambda e: e["metal"].lookup_multiplier("fire")),
        (
            ["fire", "metal"],
            "fire",
            lambda e: e["fire"].lookup_multiplier("fire")
            * e["metal"].lookup_multiplier("fire"),
        ),
        (
            ["aether", "fire"],
            "metal",
            lambda e: e["fire"].lookup_multiplier("metal"),
        ),
        (["fire", "metal"], "aether", lambda e: 1.0),
    ],
)
def test_resistance(elements, defenders, attacker, expected_fn):
    dfn = [elements[d] for d in defenders]
    score = ElementTypesHandler.calculate_resistance_multiplier_for_types(
        dfn, attacker
    )
    assert score == expected_fn(elements)
