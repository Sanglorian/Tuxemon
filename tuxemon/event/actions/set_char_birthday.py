# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import partial
from random import randint
from typing import TYPE_CHECKING, final

from tuxemon.event.eventaction import EventAction

if TYPE_CHECKING:
    from tuxemon.npc import NPC
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


@final
@dataclass
class SetPlayerBirthdayAction(EventAction):
    """
    Open the date picker to set the player's birthday.

    Script usage:
        .. code-block::

            set_char_birthday <character> [random]

    Script parameters:
        character: Either "player" or an NPC slug (e.g. "npc_maple")
        random: If provided, assigns a random birthday instead of
            opening the date picker.
    """

    name = "set_char_birthday"
    character: str
    random: str | None = None

    def set_birthday(self, character: NPC, date: tuple[int, int]) -> None:
        character.birthdate = date
        logger.debug(f"Assigned birthday {date} to {character.slug}")

    def start(self, session: Session) -> None:
        character = session.get_npc(self.character)

        if character is None:
            logger.error(f"{self.character} not found")
            return

        if self.random is not None:
            birthdate = self._generate_random_date()
            self.set_birthday(character, birthdate)
            self.stop()
            return

        session.client.push_state(
            "DatePickerState",
            callback=partial(self.set_birthday, character),
            escape_key_exits=False,
        )

    def _generate_random_date(self) -> tuple[int, int]:
        month = randint(1, 12)

        if month in (4, 6, 9, 11):
            max_days = 30
        elif month == 2:
            max_days = 29
        else:
            max_days = 31

        day = randint(1, max_days)
        return month, day

    def update(self, session: Session, dt: float) -> None:
        try:
            session.client.get_state_by_name("DatePickerState")
        except ValueError:
            self.stop()
