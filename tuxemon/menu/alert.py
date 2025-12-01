# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from tuxemon.constants.dialog_speed import resolve_character_delay
from tuxemon.prepare import CONFIG
from tuxemon.ui.text import TextArea

if TYPE_CHECKING:
    from tuxemon.event.eventbus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class AlertEntry:
    message: str
    text_area: TextArea
    callback: Optional[Callable[[], None]]
    dialog_speed: str
    split_lines: bool


class AlertManager:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self._dialog_lines: list[str] = []
        self._dialog_index: int = 0
        self._final_callback: Optional[Callable[[], None]] = None
        self._time_accum: float = 0.0
        self.character_delay = resolve_character_delay(CONFIG.dialog_speed)

        self._alert_queue: deque[AlertEntry] = deque()
        self._is_busy: bool = False
        self._active_area: Optional[TextArea] = None

    def update(self, dt: float) -> None:
        area = self._active_area
        if area is None or not area.drawing_text:
            return

        self._time_accum += dt
        while self._time_accum >= self.character_delay and area.drawing_text:
            try:
                next(area)
            except StopIteration:
                self._on_line_complete()
                break
            self._time_accum -= self.character_delay

    def _current_text_area(self) -> Optional[TextArea]:
        """Return the currently active TextArea being animated."""
        return self._active_area

    def animate_text(
        self, text_area: Optional[TextArea], text: str, dialog_speed: str
    ) -> None:
        """Animate text in the given TextArea at the specified speed."""
        if text_area is None:
            logger.error("No TextArea available to animate text.")
            return

        text_area.text = text
        self.character_delay = resolve_character_delay(dialog_speed)

        if self.character_delay == 0.0:
            try:
                for _ in text_area:
                    pass
            except Exception as e:
                logger.warning(f"Unexpected error while dumping text: {e}")
            self._on_line_complete()

    def alert(
        self,
        message: str,
        text_area: TextArea,
        callback: Optional[Callable[[], None]] = None,
        dialog_speed: str = CONFIG.dialog_speed,
        split_lines: bool = False,
    ) -> None:
        """Queue a new alert message for display in a TextArea."""
        self._alert_queue.append(
            AlertEntry(message, text_area, callback, dialog_speed, split_lines)
        )
        if not self._is_busy:
            self._process_next_alert()

    def _process_next_alert(self) -> None:
        """Start processing the next alert in the queue."""
        if self._alert_queue:
            self._is_busy = True
            next_alert = self._alert_queue.popleft()
            self._active_area = next_alert.text_area

            def alert_complete_callback() -> None:
                try:
                    if next_alert.callback:
                        next_alert.callback()
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
                finally:
                    self._finish_alert()

            self._final_callback = alert_complete_callback

            if next_alert.split_lines:
                self._dialog_lines = next_alert.message.splitlines()
                self._dialog_index = 0
                self.event_bus.publish(
                    "DIALOG_STARTED",
                    payload={
                        "state": "DialogState",
                        "message": self._dialog_lines[0],
                        "split_lines": next_alert.split_lines,
                    },
                )
                self.advance_dialog_line(
                    next_alert.dialog_speed, next_alert.text_area
                )
            else:
                self.event_bus.publish(
                    "DIALOG_STARTED",
                    payload={
                        "state": "DialogState",
                        "message": next_alert.message,
                        "split_lines": next_alert.split_lines,
                    },
                )
                self.animate_text(
                    next_alert.text_area,
                    next_alert.message,
                    next_alert.dialog_speed,
                )
        else:
            self._is_busy = False
            self._active_area = None

    def advance_dialog_line(
        self, dialog_speed: str, text_area: TextArea
    ) -> None:
        """Advance to the next line of a split-line alert."""
        if self._dialog_index < len(self._dialog_lines):
            line = self._dialog_lines[self._dialog_index]
            self._dialog_index += 1
            self.animate_text(text_area, line, dialog_speed)
        else:
            # All lines done
            self._dialog_lines = []
            self._dialog_index = 0
            self._on_alert_complete()

    def _on_line_complete(self) -> None:
        """Handle completion of a line, advancing or finishing the alert."""
        # If more lines remain, advance automatically
        if self._dialog_index < len(self._dialog_lines):
            current_area = self._current_text_area()
            if current_area:
                self.advance_dialog_line(CONFIG.dialog_speed, current_area)
        # Otherwise, finish the alert (close)
        else:
            self._on_alert_complete()

    def _on_alert_complete(self) -> None:
        """Handle completion of an alert and invoke its callback."""
        if self._final_callback:
            try:
                self._final_callback()
            except Exception as e:
                logger.error(f"Error in final callback: {e}")
            finally:
                self._final_callback = None

    def _finish_alert(self) -> None:
        """Mark the current alert as finished and process the next one."""
        self._is_busy = False
        self._process_next_alert()

    def dump_remaining_text(self, text_area: TextArea) -> None:
        """Dump all remaining characters in the current line immediately."""
        if text_area is None:
            logger.error("No TextArea available to dump remaining text.")
            return

        # Dump all remaining characters in the current line
        try:
            for _ in text_area:
                pass
        except Exception as e:
            logger.warning(f"Error dumping remaining text: {e}")

        # After dumping, handle line completion (advance or close)
        self._on_line_complete()

    def is_dialog_complete(self, text_area: TextArea) -> bool:
        """Return True if the given TextArea has finished drawing text."""
        if text_area is None:
            return True
        return not text_area.drawing_text

    def is_busy(self) -> bool:
        """Return True if the manager is currently processing an alert."""
        return self._is_busy

    def current_message(self) -> Optional[str]:
        """Return the current message line being displayed, if any."""
        if self._dialog_lines and 0 <= self._dialog_index < len(
            self._dialog_lines
        ):
            return self._dialog_lines[self._dialog_index]
        return None
