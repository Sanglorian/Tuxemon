# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.graphics import ColorLike, string_to_colorlike
from tuxemon.platform.const.graphics import BLACK_COLOR
from tuxemon.platform.const.sizes import TRANS_TIME
from tuxemon.session import Session
from tuxemon.states.world_state import WorldState

logger = logging.getLogger(__name__)


@final
@dataclass
class FarmSleepAction(EventAction):
    """
    Sleep until morning: fade out, end the farm day, and fade back in.

    The day passes while the screen is dark, so crops have already grown and
    the soil has dried by the time the player can see the farm again.

    This moves the farm calendar only. The session clock keeps reporting
    real-world time and is not touched.

    Writes the new date into the ``farm_day``, ``farm_day_of_season``,
    ``farm_season`` and ``farm_year`` game variables, so a following
    ``translated_dialog farm_new_day`` can report it.

    Script usage:
        .. code-block::

            farm_sleep [days][,trans_time][,rgb]

    Script parameters:
        days: How many days to pass. Defaults to 1.
        trans_time: Fade time in seconds, each way - default 0.3
        rgb: Fade colour (eg 255,0,0 or 255:0:0) - default black.

    eg: "farm_sleep"
    eg: "farm_sleep 1,1.5"
    """

    name = "farm_sleep"
    days: int = 1
    trans_time: float | None = None
    rgb: str | None = None
    elapsed: float = 0.0

    def start(self, session: Session) -> None:
        self._day_passed = False
        self._fade_in_triggered = False
        self.elapsed = 0.0

        self._time = TRANS_TIME if self.trans_time is None else self.trans_time
        self._rgb: ColorLike = BLACK_COLOR
        if self.rgb:
            self._rgb = string_to_colorlike(self.rgb)

        if int(self.days) < 1:
            logger.error(f"Cannot sleep for {self.days} days")
            self.stop()
            return

        if WorldState.name not in session.client.active_state_names:
            # No world to fade, so pass the night without the theatrics.
            logger.debug("Sleeping outside the world state; skipping the fade")
            self._pass_the_night(session)
            self.stop()
            return

        world = session.client.get_state_by_name(WorldState)
        world.transition_manager.fade_out(self._time, self._rgb)

    def update(self, session: Session, dt: float) -> None:
        self.elapsed += dt

        if self.elapsed >= self._time and not self._day_passed:
            self._pass_the_night(session)
            world = session.client.get_state_by_name(WorldState)
            world.transition_manager.fade_in(self._time, self._rgb)
            self._day_passed = True
            self._fade_in_triggered = True

        if self.elapsed >= 2 * self._time:
            self.stop()

    def _pass_the_night(self, session: Session) -> None:
        """Ends the farm day and records the new date for map scripts."""
        farm = session.client.farm_manager
        farm.advance_day(int(self.days))

        calendar = farm.calendar
        variables = session.player.game_variables
        variables.set("farm_day", str(calendar.day))
        variables.set("farm_day_of_season", str(calendar.day_of_season))
        variables.set("farm_season", calendar.season)
        variables.set("farm_year", str(calendar.year))
        logger.debug(
            f"Slept to farm day {calendar.day} "
            f"({calendar.season} {calendar.day_of_season})"
        )
