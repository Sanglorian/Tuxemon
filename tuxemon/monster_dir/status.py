# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from tuxemon.db import (
    CategoryStatus,
    EffectPhase,
    ResponseStatus,
)
from tuxemon.status.status import Status, decode_status, encode_status

if TYPE_CHECKING:
    from tuxemon.core.core_effect import StatusEffectResult
    from tuxemon.item.item import Item
    from tuxemon.monster import Monster
    from tuxemon.session import Session


logger = logging.getLogger(__name__)


class BlockedReason(Enum):
    IMMUNE_BY_ITEM = "immune_by_item"
    ALREADY_PRESENT = "already_present"


@dataclass
class StatusApplyResult:
    applied: bool
    blocked_by: str | None = None
    blocked_reason: BlockedReason | None = None


class MonsterStatusHandler:
    def __init__(self, status: list[Status] | None = None):
        self.status = status if status is not None else []

    @property
    def is_fainted(self) -> bool:
        return self.has_status("faint")

    @property
    def current_status(self) -> Status | None:
        if not self.status:
            return None
        return self.status[0]

    def is_blocked(self, monster: Monster, status_slug: str) -> str | None:
        """Check if the monster's held item grants immunity to the given status."""
        item = monster.held_item
        if item and item.is_immune(status_slug):
            logger.debug(
                f"Item '{item.name}' blocks status '{status_slug}' for monster '{monster.name}'."
            )
            return item.name
        return None

    def apply_status(
        self,
        session: Session,
        new_status: Status,
    ) -> StatusApplyResult:
        """
        Apply a status effect to a monster during combat by replacing or removing
        the previous status effect. Handles transition rules, immunity, stacking,
        and ON_START/ON_END effect phases.
        """
        host = new_status.host
        logger.debug(
            f"Trying to apply status '{new_status.slug}' to monster '{host.name}'."
        )

        blocked_by = self.is_blocked(host, new_status.slug)
        if blocked_by:
            logger.debug(
                f"Status '{new_status.slug}' blocked by '{blocked_by}'."
            )
            return StatusApplyResult(
                applied=False,
                blocked_by=blocked_by,
                blocked_reason=BlockedReason.IMMUNE_BY_ITEM,
            )

        current_status = self.current_status

        if current_status is None:
            logger.debug("No current status, applying new status directly.")
            self.add_status(new_status)
            new_status.tick_turn()
            new_status.use(session, EffectPhase.ON_START)
            return StatusApplyResult(applied=True)

        if self.has_status(new_status.slug):
            logger.debug(
                f"Monster already has status '{new_status.slug}', skipping."
            )
            current_status.stack()
            return StatusApplyResult(
                applied=False,
                blocked_by=current_status.name,
                blocked_reason=BlockedReason.ALREADY_PRESENT,
            )

        if current_status.category == CategoryStatus.positive:
            transition = new_status.on_positive_status
        elif current_status.category == CategoryStatus.negative:
            transition = new_status.on_negative_status
        else:
            transition = ResponseStatus.replaced

        if transition == ResponseStatus.replaced:
            current_status.use(session, EffectPhase.ON_END)

        new_status.tick_turn()
        new_status.use(session, EffectPhase.ON_START)

        if transition == ResponseStatus.replaced:
            self.add_status(new_status)
            return StatusApplyResult(applied=True)

        if transition == ResponseStatus.removed:
            self.clear_status(session)
            return StatusApplyResult(applied=False)

        return StatusApplyResult(applied=False)

    def add_status(self, status: Status) -> None:
        if self.has_status(status.slug):
            return
        self.status = [status]

    def clear_status(self, session: Session) -> None:
        """Clears the current status effect for monsters in combat."""
        current_status = self.current_status
        if current_status:
            current_status.use(session, EffectPhase.ON_END)
            self.status.clear()

    def apply_faint(self, session: Session, monster: Monster) -> None:
        self.clear_status(session)
        self.add_status(Status.create("faint", monster))

    def get_statuses(self) -> list[Status]:
        return self.status

    def has_status(self, status_slug: str) -> bool:
        return any(status_slug == status.slug for status in self.status)

    def status_exists(self) -> bool:
        return bool(self.status)

    def remove_bonded_statuses(self, session: Session) -> None:
        to_remove = [sta for sta in self.status if sta.bond]

        for sta in to_remove:
            sta.use(session, EffectPhase.ON_END)

        self.status = [sta for sta in self.status if not sta.bond]

    def check_and_clear_use_expiry(
        self, session: Session, max_uses: int = 1
    ) -> bool:
        """
        Checks if a status is expired by its use counter. If so, clears it.
        """
        current_status = self.current_status
        if current_status and current_status.is_use_expired(max_uses=max_uses):
            self.clear_status(session)
            return True
        return False

    def tick_statuses_on_steps(
        self, session: Session, steps: float
    ) -> list[StatusEffectResult]:
        """
        Calls the step tick on all active statuses and returns any effect results.
        """
        results = []
        for status in self.status:
            result = status.tick_steps(session, steps)
            if result:
                results.append(result)
        return results

    def apply_item_statuses(self, monster: Monster, item: Item) -> None:
        if not item.granted_statuses:
            return
        tech_slug = random.choice(item.granted_statuses)
        if self.has_status(tech_slug):
            return
        self.add_status(Status.create(tech_slug, monster))

    def remove_item_statuses(self, item: Item) -> None:
        granted = set(item.granted_statuses)
        self.status = [m for m in self.status if m.slug not in granted]

    def encode_status(self) -> Sequence[Mapping[str, Any]]:
        return encode_status(self.status)

    def decode_status(
        self, json_data: Mapping[str, Any] | None, monster: Monster
    ) -> None:
        if json_data is None or "status" not in json_data:
            return
        self.status = [
            cond for cond in decode_status(json_data["status"], monster)
        ]
