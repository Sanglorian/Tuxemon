# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pygame.rect import Rect

from tuxemon.constants.paths import mods_folder
from tuxemon.tools import scale_sequence

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from tuxemon.npc import NPC


def load_layout_groups(path: Path) -> dict[int, list[str]]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    raw_groups = data.get("LAYOUT_GROUPS", {})

    layout_groups = {}
    for key, layout_keys in raw_groups.items():
        try:
            num_players = int(key.split("_")[0])
            layout_groups[num_players] = layout_keys
        except (ValueError, IndexError):
            logger.warning(f"Invalid layout group key: '{key}'")
    return layout_groups


def load_layouts_from_yaml(
    path: Path,
) -> dict[str, dict[str, tuple[int, ...]]]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    raw_layouts = data.get("LAYOUT_COORDINATES", {})
    return {
        layout_name: {key: tuple(value) for key, value in layout.items()}
        for layout_name, layout in raw_layouts.items()
    }


def scale_layouts(
    layouts: dict[str, dict[str, tuple[int, ...]]],
) -> dict[str, dict[str, tuple[int, ...]]]:
    """
    Scales all position values in layout dictionaries using the configured scale factor.
    """
    scaled_layouts = {}

    for layout_name, layout in layouts.items():
        scaled_items = {}
        for key, coords in layout.items():
            scaled_items[key] = scale_sequence(coords)
        scaled_layouts[layout_name] = scaled_items

    return scaled_layouts


layouts = load_layouts_from_yaml(mods_folder / "combat_layouts.yaml")
scaled_layouts = scale_layouts(layouts)
layout_groups = load_layout_groups(mods_folder / "combat_layouts.yaml")


class LayoutManager:
    """
    Manages the combat layout coordinates for multiple players.
    Provides specific layouts based on the total number of players
    and the individual player's index.
    """

    def __init__(
        self,
        scaled_layouts: dict[str, dict[str, tuple[int, ...]]],
        layout_groups: dict[int, list[str]],
    ) -> None:
        self._layouts_by_player_count = {
            count: [scaled_layouts.get(name, {}) for name in layout_names]
            for count, layout_names in layout_groups.items()
        }

    def get_raw_layout_for_player(
        self, player_index: int, total_players: int
    ) -> dict[str, tuple[int, ...]]:
        """
        Retrieves the raw (unscaled) coordinate dictionary for a given player
        based on their index and the total number of players.

        Parameters:
            player_index: The 0-based index of the player in the list.
            total_players: The total number of players in the current combat.

        Returns:
            A dictionary containing the raw coordinate tuples for the player's layout.

        Raises:
            ValueError: If a layout is not defined for the given total number of players
                        or if the player index is out of bounds for the defined layouts.
        """
        if total_players not in self._layouts_by_player_count:
            raise ValueError(
                f"Combat layout not defined for {total_players} players."
            )

        specific_layouts = self._layouts_by_player_count[total_players]

        if not (0 <= player_index < len(specific_layouts)):
            raise IndexError(
                f"Player index {player_index} out of bounds for {total_players} player layout. "
                f"Expected index between 0 and {len(specific_layouts) - 1}."
            )

        return specific_layouts[player_index]

    def prepare_all_player_layouts(
        self, players: list[NPC]
    ) -> dict[NPC, dict[str, list[Rect]]]:
        """
        Prepares the scaled Rect layouts for all given players based on the
        current number of players.

        Parameters:
            players: A list of NPC objects representing the players in combat.

        Returns:
            A dictionary mapping each NPC player to their designated layout,
            where each layout component is a list of scaled Rect objects.
        """
        all_layouts_for_players = {}
        total_players = len(players)

        for index, player in enumerate(players):
            try:
                raw_layout = self.get_raw_layout_for_player(
                    index, total_players
                )
                scaled_layout = {
                    key: [Rect(value)] for key, value in raw_layout.items()
                }
                all_layouts_for_players[player] = scaled_layout
            except (ValueError, IndexError) as e:
                logger.error(
                    f"Error preparing layout for player {index}/{total_players}: {e}"
                )
                raise

        return all_layouts_for_players


def prepare_layout(
    players: list[NPC], layout_manager: LayoutManager
) -> dict[NPC, dict[str, list[Rect]]]:
    """
    Arranges player positions for combat using a dedicated layout manager.

    Parameters:
        players: list of NPCs to be positioned.
        layout_manager: An instance of LayoutManager to determine layouts.

    Returns:
        A dictionary mapping each player to their designated layout.
    """
    return layout_manager.prepare_all_player_layouts(players)
