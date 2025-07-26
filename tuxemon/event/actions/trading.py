# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, final
from uuid import UUID

from tuxemon.db import Acquisition, SeenStatus, db
from tuxemon.event import get_monster_by_iid
from tuxemon.event.eventaction import EventAction
from tuxemon.monster import Monster
from tuxemon.time_handler import today_ordinal

if TYPE_CHECKING:
    from tuxemon.session import Session


logger = logging.getLogger(__name__)


@final
@dataclass
class TradingAction(EventAction):
    """
    Select a monster in the player party and trade.

    Script usage:
        .. code-block::

            trading <variable>,<added>

    Script parameters:
        variable: Name of the variable where to store the monster id (removed).
        added: Slug monster or Name of the variable where to store the monster
            id (added).

    eg. "trading name_variable,apeoro"
    eg. "trading name_variable,name_variable"
    """

    name = "trading"
    variable: str
    added: str

    def start(self, session: Session) -> None:
        player = session.player
        _monster_id = UUID(player.game_variables[self.variable])
        monster_id = get_monster_by_iid(session, _monster_id)
        if monster_id is None:
            logger.error("Monster not found")
            return

        if self.added in db.database["monster"]:
            new = _create_traded_monster(monster_id, self.added)
            owner = monster_id.get_owner()
            slot = owner.monsters.index(monster_id)
            owner.party.remove_monster(monster_id)
            owner.party.add_monster(new, slot)
            owner.tuxepedia.add_entry(new.slug, SeenStatus.caught)
        else:
            _added_id = UUID(player.game_variables[self.added])
            added_id = get_monster_by_iid(session, _added_id)
            if added_id is None:
                logger.error("Monster not found")
                return
            _switch_monsters(monster_id, added_id)


def _create_traded_monster(removed: Monster, added: str) -> Monster:
    """Create a new monster with the same level and moves as the removed monster."""
    new = Monster.spawn_base(added, removed.level)
    new.set_capture(today_ordinal())
    new.set_acquisition(Acquisition.TRADED)
    return new


def _switch_monsters(removed: Monster, added: Monster) -> None:
    """Switch two monsters between their owners."""
    receiver = removed.get_owner()
    giver = added.get_owner()

    slot_removed = receiver.monsters.index(removed)
    slot_added = giver.monsters.index(added)

    removed.set_acquisition(Acquisition.TRADED)
    added.set_acquisition(Acquisition.TRADED)

    logger.info(f"{removed.name} traded for {added.name}!")
    logger.info(f"{added.name} traded for {removed.name}!")
    logger.info(f"{receiver.name} welcomes {added.name}!")
    logger.info(f"{giver.name} welcomes {removed.name}!")

    giver.party.remove_monster(removed)
    receiver.party.add_monster(added, slot_removed)
    receiver.tuxepedia.add_entry(added.slug, SeenStatus.caught)

    receiver.party.remove_monster(added)
    giver.party.add_monster(removed, slot_added)
    giver.tuxepedia.add_entry(removed.slug, SeenStatus.caught)
