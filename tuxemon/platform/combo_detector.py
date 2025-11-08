# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Optional

from tuxemon.platform.events import PlayerInput
from tuxemon.platform.tools import ButtonEdgeFilter

logger = logging.getLogger(__name__)


@dataclass
class _TrieNode:
    """A node in the combo detection Trie."""

    children: dict[int, _TrieNode] = field(default_factory=dict)
    callback: Optional[Callable[[], None]] = None
    max_delay_s: Optional[float] = None
    priority: int = 0


@dataclass
class _ActiveCombo:
    """Represents a potential combo match in progress."""

    node: _TrieNode
    last_timestamp: float


@dataclass
class ComboProfile:
    name: str
    buttons: list[int]
    callback: Callable[[], None]
    delays_ms: Optional[list[float]] = None
    description: str = ""
    character: Optional[str] = None
    difficulty: int = 1  # 1 = easy, 2 = medium, 3 = hard
    priority: int = 0


class ComboManager:
    def __init__(self) -> None:
        self.detector = ComboDetector()
        self.edge_filter = ButtonEdgeFilter()

    def process(self, event: PlayerInput) -> None:
        if self.edge_filter.is_new_press(event.button, event.pressed):
            self.detector.process_input(event)


class ComboDetector:
    """
    Detects button combinations based on a stream of inputs using a Trie.
    """

    def __init__(self) -> None:
        self._trie = _TrieNode()
        self._active_combos: list[_ActiveCombo] = []
        self._global_window_s: float = 2.0

    def add_combo(self, profile: ComboProfile) -> None:
        node = self._trie
        num_buttons = len(profile.buttons)

        has_valid_delays = (
            profile.delays_ms and len(profile.delays_ms) == num_buttons - 1
        )

        for i, button in enumerate(profile.buttons):
            if button not in node.children:
                node.children[button] = _TrieNode()

            child = node.children[button]

            if profile.delays_ms and has_valid_delays and i < num_buttons - 1:
                child.max_delay_s = profile.delays_ms[i] / 1000.0

            node = child

        node.callback = profile.callback
        node.priority = profile.priority

    def remove_combo(self, buttons: list[int]) -> bool:
        """Removes a combo pattern from the Trie."""
        path: list[tuple[int, _TrieNode]] = []
        node = self._trie

        # Traverse the Trie and record the path
        for button in buttons:
            if button not in node.children:
                return False  # Combo not found
            path.append((button, node))
            node = node.children[button]

        # Remove the callback
        if node.callback is None:
            return False  # No combo to remove
        node.callback = None
        node.priority = 0

        # Prune orphaned nodes
        for button, parent in reversed(path):
            child = parent.children[button]
            if (
                child.callback is None
                and child.priority == 0
                and not child.children
            ):
                del parent.children[button]
            else:
                break

        return True

    def process_input(self, input_event: PlayerInput) -> None:
        """
        Processes a single input event and checks for any matching combos
        by traversing the Trie.
        """
        current_time = input_event.timestamp

        fresh_active_combos: list[_ActiveCombo] = [
            ac
            for ac in self._active_combos
            if (current_time - ac.last_timestamp) <= self._global_window_s
        ]

        new_active_combos: list[_ActiveCombo] = []

        if input_event.button in self._trie.children:
            new_active_combos.append(
                _ActiveCombo(
                    self._trie.children[input_event.button], current_time
                )
            )

        for active_combo in fresh_active_combos:
            time_diff = current_time - active_combo.last_timestamp
            if input_event.button in active_combo.node.children and (
                active_combo.node.max_delay_s is None
                or time_diff <= active_combo.node.max_delay_s
            ):
                new_active_combos.append(
                    _ActiveCombo(
                        active_combo.node.children[input_event.button],
                        current_time,
                    )
                )

        completed_combos = [ac for ac in new_active_combos if ac.node.callback]

        if completed_combos:
            # Tie-breaker: highest priority, then longest sequence
            best_combo = max(
                completed_combos,
                key=lambda ac: (ac.node.priority, len(ac.node.children)),
            )

            if best_combo.node.callback:
                best_combo.node.callback()
                cb_name = str(best_combo.node.callback)
                logger.info(
                    f"Combo detected: priority={best_combo.node.priority}, callback={cb_name}"
                )
            else:
                logger.warning(
                    f"Combo node reached with priority={best_combo.node.priority} but no callback set."
                )

            self._active_combos.clear()
            return

        self._active_combos = new_active_combos
