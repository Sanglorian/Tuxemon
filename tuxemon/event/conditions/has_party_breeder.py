# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar

from tuxemon.db import EvolutionStage, GenderType, SpatialCondition
from tuxemon.event.eventcondition import EventCondition
from tuxemon.session import Session

logger = logging.getLogger(__name__)


@dataclass
class HasPartyBreederCondition(EventCondition):
    """
    Check to see if the character has a male and female
    monsters not basic (first evolution stage) in the party.

    Script usage:
        .. code-block::

            is has_party_breeder <character>

    Script parameters:
        character: Either "player" or npc slug name (e.g. "npc_maple").
    """

    name: ClassVar[str] = "has_party_breeder"
    character: str

    def test(self, session: Session, condition: SpatialCondition) -> bool:
        character = session.get_npc(self.character)
        if character is None:
            logger.error(f"{self.character} not found")
            return False

        has_male_evolved_monsters = any(
            mon.stage != EvolutionStage.BASIC and mon.gender == GenderType.MALE
            for mon in character.monsters
        )
        has_female_evolved_monsters = any(
            mon.stage != EvolutionStage.BASIC
            and mon.gender == GenderType.FEMALE
            for mon in character.monsters
        )

        return has_male_evolved_monsters and has_female_evolved_monsters
