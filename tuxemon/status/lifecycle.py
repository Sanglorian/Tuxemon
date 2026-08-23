# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations


class Lifecycle:
    """
    Handles duration, stacking, and use-based expiration for a status.

    The turn counter is one-based: gaining the status ticks it to 1, and
    every round it survives ticks it again. A status on its first round is
    therefore on turn 1, not turn 0, and effects reading ``nr_turn`` should
    be written against that. Only a status with a finite duration counts
    turns at all -- ``tick_turn`` is a no-op while duration is 0.
    """

    def __init__(self, duration: int = 0, max_stacks: int = 5) -> None:
        self.duration = duration
        self.max_stacks = max_stacks

        self.turn: int = 0
        self.stack_level: int = 1
        self.use_counter: int = 0

    def tick_turn(self) -> None:
        """Advance the turn counter if the status has a finite duration."""
        if self.duration > 0:
            self.turn += 1

    def has_exceeded_duration(self) -> bool:
        """Returns True if the status has lasted longer than its duration."""
        return self.duration > 0 and self.turn > self.duration

    def advance_use(self) -> None:
        """Increment the use counter."""
        self.use_counter += 1

    def is_use_expired(self, max_uses: int = 1) -> bool:
        """Returns True if the status has been used too many times."""
        return self.use_counter >= max_uses

    def stack(self) -> tuple[int, int]:
        """
        Increase stack level up to max_stacks and refresh duration/uses.

        Restacking puts the status back on its first turn, the same place
        gaining it fresh does.
        """
        old = self.stack_level
        self.stack_level = min(self.stack_level + 1, self.max_stacks)

        self.turn = 1 if self.duration > 0 else 0
        self.use_counter = 0

        return old, self.stack_level
