# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_condition import CoreCondition

if TYPE_CHECKING:
    from tuxemon.monster import Monster
    from tuxemon.session import Session


@dataclass
class TypeCondition(CoreCondition):
    """
    Compares the target Monster's type against the given types.

    Returns true if its equal to any of the listed types.
    """

    name = "type"
    elements: str

    def test_with_monster(self, session: Session, target: Monster) -> bool:
        elements = (
            self.elements.split(":")
            if ":" in self.elements
            else [self.elements]
        )
        return any(ele.slug in elements for ele in target.types.current)
