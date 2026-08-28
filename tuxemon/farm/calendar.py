# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from typing import Any, Final

logger = logging.getLogger(__name__)

DEFAULT_SEASON_LENGTH: Final[int] = 28
SEASONS: Final[tuple[str, ...]] = ("spring", "summer", "autumn", "winter")


class FarmCalendar:
    """
    A farm-day counter that runs alongside, and independently of, the
    real-world clock in :class:`~tuxemon.time_handler.TimeHandler`.

    ``TimeHandler`` always reports the actual system date and has no notion of
    progression. Crops need a day that only moves when the game says so, so
    the farm keeps its own count here. Nothing in this class reads or mutates
    the session clock, and removing the farm leaves the clock untouched.

    Days are one-based: a new save starts on day 1 of spring, year 1.
    """

    def __init__(self, season_length: int = DEFAULT_SEASON_LENGTH) -> None:
        if season_length < 1:
            raise ValueError("season_length must be at least 1")
        self.season_length = season_length
        self._day = 1

    @property
    def day(self) -> int:
        """The absolute farm day, counting from 1."""
        return self._day

    @property
    def day_of_season(self) -> int:
        """The one-based day within the current season."""
        return (self._day - 1) % self.season_length + 1

    @property
    def season_index(self) -> int:
        """Index into :data:`SEASONS` for the current season."""
        return ((self._day - 1) // self.season_length) % len(SEASONS)

    @property
    def season(self) -> str:
        """The current farm season, e.g. ``"spring"``."""
        return SEASONS[self.season_index]

    @property
    def year(self) -> int:
        """The one-based farm year."""
        return (self._day - 1) // (self.season_length * len(SEASONS)) + 1

    def advance_day(self, days: int = 1) -> int:
        """
        Move the calendar forward and return the new absolute day.

        Parameters:
            days: How many days to advance. Must be positive; the farm
                calendar never runs backwards.
        """
        if days < 1:
            raise ValueError("days must be at least 1")
        self._day += days
        logger.debug(
            f"Farm day advanced to {self._day} "
            f"({self.season} {self.day_of_season}, year {self.year})"
        )
        return self._day

    def days_since(self, day: int) -> int:
        """How many farm days have passed since the given absolute day."""
        return self._day - day

    def get_state(self) -> dict[str, Any]:
        """Prepares a dictionary of the calendar to be saved."""
        return {"day": self._day, "season_length": self.season_length}

    def set_state(self, save_data: dict[str, Any]) -> None:
        """Restores the calendar from saved data."""
        self.season_length = int(
            save_data.get("season_length", DEFAULT_SEASON_LENGTH)
        )
        if self.season_length < 1:
            logger.warning(
                f"Saved season_length {self.season_length} is invalid, "
                f"falling back to {DEFAULT_SEASON_LENGTH}"
            )
            self.season_length = DEFAULT_SEASON_LENGTH
        self._day = max(1, int(save_data.get("day", 1)))
