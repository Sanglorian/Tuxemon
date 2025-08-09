# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from tuxemon.db import BattleGraphicsModel
    from tuxemon.npc import NPC
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


@dataclass
class CombatContext:
    session: Session
    teams: list[NPC]
    graphics: BattleGraphicsModel
    combat_type: Literal["monster", "trainer"]
    battle_mode: Literal["single", "double"]

    def _validate_team_count(self) -> None:
        if len(self.teams) > 2:
            logger.warning(
                f"Multi-team combat detected with {len(self.teams)} teams."
            )
            raise NotImplementedError(
                "Multi-team combat is not yet supported."
            )

    def __post_init__(self) -> None:
        self._validate_team_count()
