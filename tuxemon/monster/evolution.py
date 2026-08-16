# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from tuxemon.database.runtime import db
from tuxemon.db import (
    LearningMethod,
    MonsterEvolutionItemModel,
    MonsterModel,
)
from tuxemon.monster.evolution_conditions import (
    check_bond,
    check_location_items_moves,
    check_party_conditions,
    check_simple_conditions,
    check_stats,
    check_tastes,
    check_variables,
)
from tuxemon.technique.technique import Technique

if TYPE_CHECKING:
    from tuxemon.entity.npc import NPC
    from tuxemon.item.item import Item
    from tuxemon.monster.evolution_registry import EvolutionRegistry
    from tuxemon.monster.monster import Monster

logger = logging.getLogger(__name__)


class Evolution:
    def __init__(self, monster: Monster):
        self.monster = monster

    def get_eligible_evolution_slug(
        self, context: dict[str, bool] | None = None
    ) -> str | None:
        """Checks all paths. Returns target slug or None."""
        if not self.is_eligible_for_evolution():
            return None

        ctx = context or {"use_item": False}
        owner = self.monster.get_owner()
        registry = owner.evolution_registry
        monster_id = self.monster.instance_id

        if not ctx.get("use_item"):
            held = self.monster.held_item
            if held and held.behaviors.block_evolution:
                return None

        blocked = registry.get_blocked(monster_id)

        for evolution_item in self.monster.evolutions:
            slug = evolution_item.monster_slug
            if slug in blocked:
                continue
            if self.can_evolve(evolution_item, ctx, owner):
                return slug

        return None

    def has_evolution_to(self, slug: str) -> bool:
        return any(
            evolution.monster_slug == slug
            for evolution in self.monster.evolutions
        )

    def has_history_to(self, slug: str) -> bool:
        return any(
            history.slug == slug
            or slug in history.evolves_from
            or slug in history.evolves_into
            for history in self.monster.history
        )

    def is_valid_evolution_target(self, target_slug: str) -> bool:
        """
        Checks if the target slug is a possible direct evolution from this
        monster or exists anywhere in its evolutionary history/future.
        """
        return self.has_evolution_to(target_slug) or self.has_history_to(
            target_slug
        )

    def confirm_pending_evolution(
        self, registry: EvolutionRegistry, evolution_slug: str
    ) -> None:
        """Confirms a pending evolution and cleans up registry state."""
        registry.clear_missed(self.monster.instance_id, evolution_slug)
        registry.clear_pending(self.monster.instance_id)
        self.monster.experience_handler.reset_status_flags()

        logger.info(
            f"Confirmed evolution of {self.monster.name}. Registry cleanup complete."
        )

    def deny_pending_evolution(
        self, registry: EvolutionRegistry, evolution_slug: str
    ) -> None:
        """Logs a missed evolution, cleans up registry state."""
        self.monster.experience_handler.reset_status_flags()
        registry.log_missed(
            self.monster.instance_id, evolution_slug, self.monster.level
        )
        registry.clear_pending(self.monster.instance_id)
        logger.info(
            f"Denied evolution of {self.monster.name}. Missed evolution logged at level {self.monster.level}."
        )

    def is_eligible_for_evolution(self) -> bool:
        return (
            self.monster.owner is not None
            and self.monster in self.monster.owner.monsters
        )

    def evolve_monster(self, new_monster: Monster) -> None:
        if not self.is_eligible_for_evolution():
            logger.warning(
                f"evolve_monster called on {self.monster} but it is not eligible for evolution."
            )
            return

        owner = self.monster.get_owner()

        self.adopt_species_moveset(new_monster)

        for move in new_monster.moves.moveset:
            if move.learning_method == LearningMethod.EVOLUTION:
                new_monster.moves.learn_by_method(
                    new_monster,
                    move.technique,
                    move.learning_method,
                )

        self.learn_missed_moves(new_monster)

        if owner.party.replace_monster(self.monster, new_monster):
            owner.tuxepedia.register_caught(new_monster.slug)
            logger.info(f"{self.monster} evolved into {new_monster}")
        else:
            logger.warning(f"Failed to evolve {self.monster}")

    def adopt_species_moveset(self, new_monster: Monster) -> None:
        """
        Gives the evolved monster the moveset of its own species.

        ``Monster.transfer_properties_from`` hands the evolved monster the
        pre-evolution's move handler so that the moves already learned carry
        over, but that handler also carries the pre-evolution's moveset. Left
        alone, the evolved form would keep consulting the previous species'
        learn list on every future level up.
        """
        species = MonsterModel.lookup(new_monster.slug, db)
        new_monster.moves.set_moveset(species.moveset or [])

    def evolution_level(self, new_monster: Monster) -> int | None:
        """
        Gets the level at which this evolution became available, if any.

        Returns None when the evolution isn't gated on a level (item, steps,
        bond, ...), and for devolutions, where the target is reached through
        the monster's history rather than its evolution paths.
        """
        levels = [
            evolution.at_level
            for evolution in self.monster.evolutions
            if evolution.monster_slug == new_monster.slug
            and evolution.at_level is not None
        ]
        return min(levels) if levels else None

    def learn_missed_moves(self, new_monster: Monster) -> list[Technique]:
        """
        Teaches the evolved form the moves it skipped while waiting to evolve.

        A monster keeps levelling as its pre-evolution until the player
        confirms the evolution, and those levels are resolved against the
        pre-evolution's moveset. Any move the evolved form teaches between its
        evolution level and the level actually reached would otherwise be
        skipped for good, since a level up only ever looks at the levels it
        just gained.

        Only that missed window is caught up: moves the evolved form teaches
        at or below its evolution level belong to the branch the player didn't
        take, and are left alone.
        """
        at_level = self.evolution_level(new_monster)
        if at_level is None or new_monster.level <= at_level:
            return []

        moves = new_monster.moves
        known = {move.slug for move in moves.get_moves()}
        learned: list[Technique] = []

        for entry in moves.moveset:
            if entry.technique in known or entry.level_learned <= at_level:
                continue
            if not moves.is_eligible(
                new_monster, entry.technique, LearningMethod.LEVEL_UP
            ):
                continue

            technique = Technique.create(entry.technique)
            if moves.learn(
                new_monster, technique, method=LearningMethod.LEVEL_UP
            ):
                known.add(technique.slug)
                learned.append(technique)

        if learned:
            logger.info(
                f"{new_monster.name} caught up on "
                f"{[technique.slug for technique in learned]}, missed between "
                f"level {at_level} and {new_monster.level} while unevolved."
            )

        return learned

    def can_evolve(
        self,
        evolution_item: MonsterEvolutionItemModel,
        context: dict[str, bool],
        owner: NPC | None = None,
    ) -> bool:
        """Checks if a monster can evolve based on conditions."""
        if self.monster.owner is None:
            return False

        if evolution_item.monster_slug == self.monster.slug:
            return False

        owner = owner or self.monster.get_owner()
        conditions: list[bool] = []

        check_simple_conditions(self.monster, evolution_item, conditions)
        check_location_items_moves(
            self.monster, evolution_item, context, conditions
        )
        check_tastes(self.monster, evolution_item, conditions)
        check_stats(self.monster, evolution_item, conditions)
        check_variables(self.monster, evolution_item, conditions)
        check_bond(self.monster, evolution_item, conditions)

        if evolution_item.party_conditions is not None:
            conditions.append(
                check_party_conditions(
                    owner.party, evolution_item.party_conditions
                )
            )

        if evolution_item.item is not None and not context.get(
            "use_item", False
        ):
            return False

        if not conditions and evolution_item.probability is not None:
            return random.random() <= evolution_item.probability

        if all(conditions):
            if evolution_item.probability is not None:
                return random.random() <= evolution_item.probability
            return True

        return False

    def get_possible_item_evolutions(
        self, item: Item, context: dict[str, bool]
    ) -> list[tuple[MonsterEvolutionItemModel, float]]:
        """
        Filters and returns evolution models possible with the given item,
        along with their weights.
        """
        possible_evolutions = []

        for evolution_model in self.monster.evolutions:
            item_weights = evolution_model.item

            if isinstance(item_weights, dict) and item.slug in item_weights:
                weight = item_weights[item.slug]

                if weight > 0.0 and self.can_evolve(evolution_model, context):
                    possible_evolutions.append((evolution_model, weight))

        return possible_evolutions

    def choose_evolution_model(
        self,
        possible_evolutions: list[tuple[MonsterEvolutionItemModel, float]],
    ) -> MonsterEvolutionItemModel:
        if not possible_evolutions:
            raise ValueError("No possible evolutions to choose from.")
        if len(possible_evolutions) == 1:
            return possible_evolutions[0][0]
        models = [e[0] for e in possible_evolutions]
        weights = [e[1] for e in possible_evolutions]
        return random.choices(models, weights=weights, k=1)[0]
