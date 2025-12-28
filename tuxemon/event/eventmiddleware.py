# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from tuxemon.platform.const import events
from tuxemon.platform.events import PlayerInput
from tuxemon.platform.tools import keymap, unicode_map

logger = logging.getLogger(__name__)


class EventMiddleware(ABC):
    """Base class for event processing middleware."""

    @abstractmethod
    def preprocess(self, event: PlayerInput) -> Optional[PlayerInput]:
        """
        Called before state propagation.

        Returns:
            The event, a modified event, or None to consume/stop propagation.
        """

    @abstractmethod
    def postprocess(
        self, processed_event: Optional[PlayerInput]
    ) -> Optional[PlayerInput]:
        """
        Called after state propagation.

        Returns:
            The final processed event, or None.
        """


class InputTranslatorMiddleware(EventMiddleware):

    def preprocess(self, event: PlayerInput) -> Optional[PlayerInput]:
        new_button_id = event.button

        if event.button in keymap:
            new_button_id = keymap[event.button]
        elif event.button == events.UNICODE and event.value in unicode_map:
            new_button_id = unicode_map[event.value]

        return PlayerInput(
            button=new_button_id,
            value=event.value,
            hold_time=event.hold_time,
            previous_value=event.previous_value,
            timestamp=event.timestamp,
            hold_duration=event.hold_duration,
        )

    def postprocess(
        self, processed_event: Optional[PlayerInput]
    ) -> Optional[PlayerInput]:
        return processed_event


class ButtonFilterMiddleware(EventMiddleware):
    """
    Filters events based on a set of raw hardware button IDs.

    Purpose: Blocks input from specific physical keys/buttons before
    they are translated into game intentions.
    """

    def __init__(self, initially_blocked_buttons: Optional[set[int]] = None):
        self._blocked_buttons: set[int] = (
            initially_blocked_buttons if initially_blocked_buttons else set()
        )

    def block_button(self, button_id: int) -> None:
        """Adds a raw button ID to the filter list."""
        self._blocked_buttons.add(button_id)
        logger.debug(f"Button filter blocking ID: {button_id}")

    def unblock_button(self, button_id: int) -> None:
        """Removes a raw button ID from the filter list."""
        self._blocked_buttons.discard(button_id)
        logger.debug(f"Button filter unblocking ID: {button_id}")

    def preprocess(self, event: PlayerInput) -> Optional[PlayerInput]:
        raw_button_id = event.button

        if raw_button_id in self._blocked_buttons:
            logger.debug(
                f"Consumed event: Raw button ID {raw_button_id} is blocked by ButtonFilter."
            )
            return None

        return event

    def postprocess(
        self, processed_event: Optional[PlayerInput]
    ) -> Optional[PlayerInput]:
        return processed_event


class IntentionFilterMiddleware(EventMiddleware):
    """
    Filters events based on a list of currently allowed/disallowed intentions.

    Purpose: Acts as a context-dependent gate to lock/allow specific game actions
    based on the current state (e.g., in a menu or cutscene).
    """

    OPEN_GATE = "OPEN_GATE"

    def __init__(self) -> None:
        self.allowed_actions: set[Any] = set()

    def update_allowed_actions(self, actions_to_allow: set[int] | str) -> None:
        """
        Configures the gate: either a set of allowed intention IDs, or the
        string 'OPEN_GATE' to allow everything.
        """
        if (
            isinstance(actions_to_allow, str)
            and actions_to_allow == self.OPEN_GATE
        ):
            self.allowed_actions = {self.OPEN_GATE}
            logger.info("Intention Gate set to ALLOW ALL.")
        else:
            self.allowed_actions = set(actions_to_allow)
            logger.info(
                f"Intention Gate updated. Allowed actions: {self.allowed_actions}"
            )

    def preprocess(self, event: PlayerInput) -> Optional[PlayerInput]:
        if self.OPEN_GATE in self.allowed_actions:
            return event

        action_id = event.button

        if not self.allowed_actions:
            logger.debug(f"Consumed intention {action_id}: Global block.")
            return None

        if action_id not in self.allowed_actions:
            logger.debug(
                f"Consumed intention {action_id}: Not on the allowed list."
            )
            return None

        return event

    def postprocess(
        self, processed_event: Optional[PlayerInput]
    ) -> Optional[PlayerInput]:
        return processed_event
