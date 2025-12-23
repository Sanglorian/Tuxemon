# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuxemon.database.validator import Validator


class _ValidatorProxy:
    _instance = None

    def set(self, instance: Validator) -> None:
        self._instance = instance

    def __getattr__(self, name: Any) -> Any:
        if self._instance is None:
            raise RuntimeError(...)
        return getattr(self._instance, name)


validator = _ValidatorProxy()
