# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
The bag decides whether to offer Use before anything else happens.

It used to ask only "can this be used on one of your monsters", which meant
an item that is used on the world rather than on a monster was refused
outright whenever the party was empty — a fishing rod with no team, a hoe
before you have caught anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tuxemon.states.item_menu import has_valid_target


@dataclass
class FakeBehaviors:
    requires_monster_menu: bool


@dataclass
class FakeItem:
    """Stands in for an Item; only the two things the gate reads."""

    requires_monster_menu: bool
    valid_for: set[object] = field(default_factory=set)
    valid_without_target: bool = True

    @property
    def behaviors(self) -> FakeBehaviors:
        return FakeBehaviors(self.requires_monster_menu)

    def validate_monster(self, session: object, target: object) -> bool:
        if target is None:
            return self.valid_without_target
        return target in self.valid_for


SESSION = object()
ROCKITTEN = object()
NUT = object()


def test_a_world_item_is_offered_with_an_empty_party():
    hoe = FakeItem(requires_monster_menu=False)
    assert has_valid_target(SESSION, hoe, [])


def test_a_world_item_still_answers_to_its_own_conditions():
    """
    A fishing rod away from water must still be refused — the fix must not
    turn the gate off, only stop it depending on the party.
    """
    rod = FakeItem(requires_monster_menu=False, valid_without_target=False)
    assert not has_valid_target(SESSION, rod, [])
    assert not has_valid_target(SESSION, rod, [ROCKITTEN])


def test_a_world_item_ignores_the_party_entirely():
    hoe = FakeItem(requires_monster_menu=False)
    assert has_valid_target(SESSION, hoe, [ROCKITTEN, NUT])


def test_a_monster_item_needs_a_monster_that_accepts_it():
    potion = FakeItem(requires_monster_menu=True, valid_for={ROCKITTEN})

    assert not has_valid_target(SESSION, potion, [])
    assert not has_valid_target(SESSION, potion, [NUT])
    assert has_valid_target(SESSION, potion, [NUT, ROCKITTEN])


def test_a_monster_item_is_not_rescued_by_the_no_target_path():
    """
    The no-target check must stay on the world branch. If it leaked into the
    monster branch, a potion would be offered with nothing to drink it.
    """
    potion = FakeItem(
        requires_monster_menu=True,
        valid_for=set(),
        valid_without_target=True,
    )
    assert not has_valid_target(SESSION, potion, [])
