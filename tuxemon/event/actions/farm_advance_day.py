# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.session import Session

logger = logging.getLogger(__name__)


@final
@dataclass
class FarmAdvanceDayAction(EventAction):
    """
    End the farm day: grow every watered crop, dry the soil, and move the
    farm calendar forward. This is what a bed calls.

    The farm calendar is separate from the session clock, which continues to
    report real-world time and is not touched by this action.

    Writes the new date into the ``farm_day``, ``farm_day_of_season``,
    ``farm_season`` and ``farm_year`` game variables.

    Script usage:
        .. code-block::

            farm_advance_day [days]

    Script parameters:
        days: How many days to pass. Defaults to 1.
    """

    name = "farm_advance_day"
    days: int = 1

    def start(self, session: Session) -> None:
        days = int(self.days)
        if days < 1:
            logger.error(f"Cannot advance the farm by {days} days")
            return

        farm = session.client.farm_manager
        farm.advance_day(days)

        variables = session.player.game_variables
        variables.set("farm_day", str(farm.calendar.day))
        variables.set("farm_day_of_season", str(farm.calendar.day_of_season))
        variables.set("farm_season", farm.calendar.season)
        variables.set("farm_year", str(farm.calendar.year))
        logger.debug(
            f"Farm day is now {farm.calendar.day} "
            f"({farm.calendar.season} {farm.calendar.day_of_season})"
        )
