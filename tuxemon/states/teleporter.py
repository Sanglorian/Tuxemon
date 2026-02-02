# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from typing import ClassVar

from tuxemon.platform.events import PlayerInput
from tuxemon.state.state import State


class TeleporterState(State):
    """State during teleport."""

    name: ClassVar[str] = "TeleporterState"
    transparent = True

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        return None
