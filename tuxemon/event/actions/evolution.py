# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, final
from uuid import UUID

from tuxemon.event.eventaction import EventAction
from tuxemon.locale.locale import T
from tuxemon.monster.monster import Monster
from tuxemon.tools import get_valid_uuid, open_choice_dialog, open_dialog
from tuxemon.ui.menu_options import MenuOptions, create_yes_no_options

if TYPE_CHECKING:
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


@final
@dataclass
class EvolutionAction(EventAction):
    """
    Checks, asks and evolves.

    Script usage:
        .. code-block::

            evolution <character>

    Script parameters:
        character: Either "player" or npc slug name (e.g. "npc_maple").
        variable: Name of the variable where to store the monster id. If no
            variable is specified, all monsters get experience.
        evolution: Slug of the evolution.
    """

    name = "evolution"
    npc_slug: str
    variable: str | None = None
    evolution: str | None = None

    def start(self, session: Session) -> None:
        self.session = session
        self.client = session.client
        character = session.get_npc(self.npc_slug)

        if character is None:
            logger.error(f"{self.npc_slug} not found")
            return

        self.char = character

        if self.client.has_extra_states():
            return

        self._pending_map: dict[UUID, str] = {}

        if self.variable is None and self.evolution is None:
            self.process_pending_evolutions()
        elif self.variable is not None and self.evolution is not None:
            self.process_direct_evolutions(self.variable, self.evolution)
        else:
            raise ValueError(
                "Both variable and evolution must be either None or not None"
            )

    def process_direct_evolutions(self, variable: str, evolution: str) -> None:
        """Process direct evolutions for the character"""
        monster_id = get_valid_uuid(self.char.game_variables, variable)
        if monster_id is None:
            logger.info(f"No valid monster selected for variable '{variable}'")
            return  # Exit early if no valid UUID

        monster = self.client.get_monster_by_iid(monster_id)

        if monster is None:
            logger.error(f"Monster '{monster_id}' doesn't exist.")
            return

        if not monster.evolution_handler.is_valid_evolution_target(evolution):
            logger.error(
                f"Monster '{evolution}' isn't in the evolutionary path."
            )
            return

        evolved = Monster.spawn_base(evolution, monster.level)
        monster.evolution_handler.evolve_monster(evolved)
        self.client.push_state(
            "EvolutionTransition", original=monster.slug, evolved=evolved.slug
        )

    def process_pending_evolutions(self) -> None:
        """Process pending evolutions for the character"""
        candidates = [m for m in self.char.monsters if m.waiting_to_evolve]
        if not candidates:
            return

        monster = candidates[0]
        context = {"use_item": monster.waiting_to_evolve}
        slug = monster.evolution_handler.get_eligible_evolution_slug(context)

        if not slug:
            monster.waiting_to_evolve = False
            return

        registry = self.char.evolution_registry
        if slug not in registry.get_pending(monster.instance_id):
            registry.add_pending(monster.instance_id, slug)

        evolved = Monster.spawn_base(slug, monster.level)
        self._pending_map[monster.instance_id] = slug
        self.question_evolution(monster, evolved)

    def question_evolution(self, monster: Monster, evolved: Monster) -> None:
        """Ask the user to confirm the evolution"""
        params = {
            "name": monster.name.upper(),
            "evolve": evolved.name.upper(),
        }
        msg = T.format("evolution_confirmation", params)
        open_dialog(self.session.client, [msg], dialog_speed="max")

        options = create_yes_no_options(
            yes_action=partial(self.confirm_evolution, monster, evolved),
            no_action=partial(self.deny_evolution, monster),
            reverse_order=True,
        )
        open_choice_dialog(self.session.client, MenuOptions(options))

    def confirm_evolution(self, monster: Monster, evolved: Monster) -> None:
        self.client.pop_state()
        self.client.pop_state()

        registry = self.char.evolution_registry
        monster.evolution_handler.confirm_pending_evolution(
            registry, evolved.slug
        )
        monster.evolution_handler.evolve_monster(evolved)
        monster.waiting_to_evolve = False

        self.client.push_state(
            "EvolutionTransition", original=monster.slug, evolved=evolved.slug
        )

    def deny_evolution(self, monster: Monster) -> None:
        monster.waiting_to_evolve = False
        slug = self._pending_map.get(monster.instance_id)
        if slug:
            registry = self.char.evolution_registry
            registry.log_missed(monster.instance_id, slug, monster.level)
            registry.clear_pending_slug(monster.instance_id, slug)

        self.client.pop_state()
        self.client.pop_state()
