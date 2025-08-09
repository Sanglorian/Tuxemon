# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any, Optional
from uuid import UUID, uuid4

from tuxemon.db import OutputBattle

logger = logging.getLogger(__name__)

SIMPLE_PERSISTANCE_ATTRIBUTES = (
    "fighter",
    "opponent",
    "outcome",
    "steps",
)


class Battle:
    """
    Tuxemon Battle.
    """

    def __init__(self, save_data: Optional[Mapping[str, Any]] = None) -> None:
        save_data = save_data or {}

        self.instance_id: UUID = uuid4()
        self.fighter: str = ""
        self.opponent: str = ""
        self.outcome: OutputBattle = OutputBattle.draw
        self.steps: int = 0

        self.set_state(save_data)

    def get_state(self) -> Mapping[str, Any]:
        """
        Prepares a dictionary of the battle to be saved to a file.

        Returns:
            Dictionary containing all the information about the battle.
        """
        save_data = {
            attr: getattr(self, attr)
            for attr in SIMPLE_PERSISTANCE_ATTRIBUTES
            if getattr(self, attr)
        }

        save_data["instance_id"] = str(self.instance_id.hex)

        return save_data

    def set_state(self, save_data: Mapping[str, Any]) -> None:
        """
        Loads information from saved data.

        Parameters:
            save_data: Data used to reconstruct the battle.
        """
        if not save_data:
            return

        for key, value in save_data.items():
            if key == "instance_id" and value:
                self.instance_id = UUID(value)
            elif key in SIMPLE_PERSISTANCE_ATTRIBUTES:
                setattr(self, key, value)


class BattlesHandler:
    """
    Handles the battles associated with an Entity.
    """

    def __init__(self, initial_battles: Optional[list[Battle]] = None) -> None:
        self._battles = initial_battles if initial_battles is not None else []

    def add_battle(self, battle: Battle) -> None:
        self._battles.append(battle)

    def get_battles(self) -> list[Battle]:
        return list(self._battles)

    def clear_battles(self) -> None:
        self._battles.clear()

    def has_fought_and_outcome(
        self, fighter: str, outcome: str, opponent: str
    ) -> bool:
        """
        Checks if a specific battle outcome has occurred between the fighter and opponent.
        This checks if there's at least one battle matching the criteria.
        """
        if outcome not in [o.value for o in OutputBattle]:
            logger.error(f"'{outcome}' isn't a valid battle outcome.")
            return False

        for battle in reversed(self._battles):
            if (
                battle.fighter == fighter
                and battle.opponent == opponent
                and battle.outcome == outcome
            ):
                return True
        return False

    def get_last_battle(self) -> Optional[Battle]:
        if self._battles:
            return self._battles[-1]
        return None

    def get_last_battle_outcome(
        self, fighter: str, opponent: str
    ) -> Optional[str]:
        """
        Returns the outcome of the last battle between the specified fighter and opponent.
        """
        for battle in reversed(self._battles):
            if battle.fighter == fighter and battle.opponent == opponent:
                return battle.outcome
        return None

    def get_battle_outcome_stats(
        self, fighter: str
    ) -> dict[OutputBattle, int]:
        """
        Returns the battle outcome statistics for the specified fighter.

        The statistics include the number of wins, losses, and draws.
        """
        battle_outcomes = {outcome: 0 for outcome in OutputBattle}

        for battle in self._battles:
            if battle.fighter == fighter:
                battle_outcomes[battle.outcome] += 1

        return battle_outcomes

    def get_battle_outcome_summary(self, fighter: str) -> dict[str, int]:
        """
        Returns a summary of the battle outcome statistics for the specified fighter.

        The summary includes the total number of battles, wins, losses, and draws.
        """
        battle_outcomes = self.get_battle_outcome_stats(fighter)
        total_battles = sum(battle_outcomes.values())

        return {
            "total": total_battles,
            "won": battle_outcomes[OutputBattle.won],
            "lost": battle_outcomes[OutputBattle.lost],
            "draw": battle_outcomes[OutputBattle.draw],
        }

    def encode_battle(self) -> Sequence[Mapping[str, Any]]:
        return encode_battle(self._battles)

    def decode_battle(self, json_data: Optional[Mapping[str, Any]]) -> None:
        if json_data and "battles" in json_data:
            self._battles = [
                bat for bat in decode_battle(json_data["battles"])
            ]


def decode_battle(
    json_data: Optional[Sequence[Mapping[str, Any]]],
) -> list[Battle]:
    return [Battle(save_data=battle) for battle in json_data or {}]


def encode_battle(battles: Sequence[Battle]) -> Sequence[Mapping[str, Any]]:
    return [battle.get_state() for battle in battles]
