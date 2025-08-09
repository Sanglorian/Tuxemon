# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import final
from uuid import UUID

from tuxemon.event import get_monster_by_iid
from tuxemon.event.eventaction import EventAction
from tuxemon.session import Session
from tuxemon.taste import Taste

logger = logging.getLogger(__name__)


@final
@dataclass
class ChangeTasteAction(EventAction):
    """
    Changes the specified taste (warm or cold) of a monster.

    Script usage:
        .. code-block::

            change_taste <variable>,<type_taste>,<new_taste>

    Script parameters:
        variable: Name of the game variable containing the monster's UUID.
        type_taste: Either "warm" or "cold" to indicate which taste to change.
        new_taste: Slug of the new taste to assign, or "random" to select a new one
            at random (excluding "tasteless" and the current taste).

    Notes:
        - When using "random", the new taste is chosen based on rarity_score weighting.
        - When specifying a taste slug, it must exist, match the selected type,
            and must not be "tasteless".
        - If no valid taste is found during random selection, the taste remains unchanged
            and a warning is logged.
    """

    name = "change_taste"
    variable: str
    type_taste: str
    new_taste: str

    def start(self, session: Session) -> None:
        player = session.player

        if self.variable not in player.game_variables:
            logger.error(f"Game variable {self.variable} not found")
            return

        monster_id = UUID(player.game_variables[self.variable])
        monster = get_monster_by_iid(session, monster_id)
        if monster is None:
            logger.error("Monster not found")
            return

        if self.new_taste == "tasteless":
            logger.error("Cannot assign 'tasteless' explicitly.")
            return

        if self.type_taste not in ("warm", "cold"):
            raise ValueError(
                f"Invalid taste type '{self.type_taste}'. Must be 'warm' or 'cold'."
            )

        current_taste = getattr(monster, f"taste_{self.type_taste}")
        if self.new_taste == "random":
            new_taste = Taste.get_random_taste_excluding(
                self.type_taste,
                exclude_slugs=[current_taste, "tasteless"],
                use_rarity=True,
            )

            if not new_taste:
                logger.warning(
                    f"No alternate {self.type_taste} taste found for {monster.name}."
                )
                return
        else:
            taste_obj = Taste.get_taste(self.new_taste)
            if not taste_obj:
                logger.error(f"Taste '{self.new_taste}' not found.")
                return

            if taste_obj.taste_type != self.type_taste:
                logger.error(
                    f"Taste '{self.new_taste}' is of type '{taste_obj.taste_type}', "
                    f"expected '{self.type_taste}'."
                )
                return

            new_taste = self.new_taste

        setattr(monster, f"taste_{self.type_taste}", new_taste)
        monster.set_stats()
        logger.info(
            f"{monster.name}'s {self.type_taste} taste changed to {new_taste}."
        )
