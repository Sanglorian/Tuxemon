# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from tuxemon import save
from tuxemon.save import get_save_path

if TYPE_CHECKING:
    from tuxemon.save_state import SaveData
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


class SaveManager:
    @staticmethod
    def exists(slot: int) -> bool:
        return Path(get_save_path(slot)).exists()

    @staticmethod
    def load(slot: int) -> SaveData | None:
        return save.load(get_save_path(slot))

    @staticmethod
    def delete(slot: int) -> bool:
        path = Path(get_save_path(slot))
        if not path.exists():
            logger.warning(f"Save slot {slot} does not exist.")
            return False
        try:
            path.unlink()
            logger.info(f"Deleted save slot {slot}.")
            return True
        except OSError as e:
            logger.error(f"Failed to delete save slot {slot}: {e}")
            return False

    @staticmethod
    def save(session: Session, slot: int) -> None:
        """
        Save both index and slot as the same number.
        This matches how save_state() is used in the engine.
        """
        session.save_state(index=slot, slot=slot)
