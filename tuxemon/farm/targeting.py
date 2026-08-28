# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final, NamedTuple

from tuxemon.map.map import get_next_tile_pos

if TYPE_CHECKING:
    from tuxemon.farm.grid import TilePos
    from tuxemon.session import Session

logger = logging.getLogger(__name__)

RESULT_VARIABLE: Final[str] = "farm_result"


class FarmTarget(NamedTuple):
    """The tile a character is working on, and the map it belongs to."""

    map_slug: str
    pos: TilePos


def resolve_target(session: Session, character: str) -> FarmTarget | None:
    """
    Returns the tile directly in front of a character.

    Farm tools act on the tile you are facing, the same one
    ``char_facing_tile`` and ``to_use_tile`` already test against. Returns
    ``None`` if the character or the current map cannot be resolved.
    """
    npc = session.client.get_npc(character)
    if npc is None:
        logger.error(f"{character} not found")
        return None

    map_slug = session.client.map_manager.map_slug
    if not map_slug:
        logger.error("No map is currently loaded")
        return None

    return FarmTarget(map_slug, get_next_tile_pos(npc.tile_pos, npc.facing))


def set_result(session: Session, success: bool) -> None:
    """
    Records whether a farm action succeeded, so map scripts can branch on it.

    Reads back as the ``farm_result`` game variable, ``"true"`` or
    ``"false"``.
    """
    session.player.game_variables.set(
        RESULT_VARIABLE, "true" if success else "false"
    )
