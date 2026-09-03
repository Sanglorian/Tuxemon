# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Working out which tile a character is aiming a farming action at.

Shared by the item effects (plant, water) and the harvest event action so
they all agree on "the tile in front of you".
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tuxemon.map.map import get_next_tile_pos

if TYPE_CHECKING:
    from tuxemon.session import Session

logger = logging.getLogger(__name__)

TilePos = tuple[int, int]


def faced_tile(
    session: Session, character_slug: str = "player"
) -> tuple[str, TilePos] | None:
    """
    The map and tile the character is standing in front of.

    Parameters:
        session: Game session.
        character_slug: "player", or an NPC slug.

    Returns:
        ``(map slug, tile position)``, or None if the character is missing.
    """
    character = session.client.get_npc(character_slug)
    if character is None:
        logger.error(f"Character '{character_slug}' not found.")
        return None

    return (
        session.client.map_manager.map_slug,
        get_next_tile_pos(character.tile_pos, character.facing),
    )
