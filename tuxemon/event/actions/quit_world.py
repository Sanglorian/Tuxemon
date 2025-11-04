# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, final

from tuxemon.event.eventaction import EventAction

if TYPE_CHECKING:
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


@final
@dataclass
class QuitWorldAction(EventAction):
    """
    Exit the current world without quitting the game.

    Script usage:
        .. code-block::

            quit_world
    """

    name = "quit_world"

    def start(self, session: Session) -> None:
        session.reset(reset_client=False)
        session.reset_time()
        session.client.current_music.stop()
        session.client.replace_state("StartState")

        session.client.event_persist.storage = defaultdict(dict)
        logger.debug("Event persistence storage cleared.")

        session.client.map_manager.current_map = None
        session.client.map_manager.maps = {}
        session.client.map_manager._map_type_slug = None
        logger.debug("Map manager state cleared.")

        session.client.npc_manager.clear_npcs()
        logger.debug("NPC manager cleared.")

        session.client.boundary.boundaries = {}
        session.client.boundary.active = None
        session.client.boundary.reset_to_default()
        logger.debug("Boundary checker cleared and reset to default.")

        session.client.camera_manager.reset()
        session.client.reset_renderer()
