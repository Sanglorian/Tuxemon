# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from tuxemon.base_client import BaseClient, ClientState

if TYPE_CHECKING:
    from tuxemon.config import TuxemonConfig
    from tuxemon.prepare import DisplayContext

logger = logging.getLogger(__name__)


class HeadlessClient(BaseClient):
    """
    Headless client for server-side processing of game logic.
    This client runs without graphics, only handling events and
    game state updates.

    Parameters:
        config: The configuration for the game.
    """

    def __init__(self, config: TuxemonConfig, context: DisplayContext) -> None:
        super().__init__(config, context)

    def main(self) -> None:
        """
        Initiates the main game loop.

        Since we are using Asteria networking to handle network events,
        we pass this session.Client instance to networking which in turn
        executes the "main_loop" method every frame.
        This leaves the networking component responsible for the main loop.
        """
        update = self.update
        clock = time.time
        time_since_draw = 0.0
        last_update = clock()

        while self.state != ClientState.DONE:
            if self.state == ClientState.RUNNING:
                clock_tick = clock() - last_update
                last_update = clock()
                time_since_draw += clock_tick
                update(clock_tick)
                time.sleep(0.01)
            elif self.state == ClientState.EXITING:
                self.perform_cleanup()
                self.state = ClientState.DONE

    def queue_command(self, command: Callable[[], None]) -> None:
        self.command_queue.put(command)
        logger.debug("Queued command for execution in main thread.")

    def update(self, time_delta: float) -> None:
        """
        Main loop for entire game.

        Parameters:
            time_delta: Elapsed time since last frame.
        """
        self.update_states(time_delta)
