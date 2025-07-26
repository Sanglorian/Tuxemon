# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations


class CurrencyFormatter:
    """Formats a monetary value with a currency symbol."""

    def __init__(self, symbol: str = "$", position: str = "before") -> None:
        self.symbol = symbol
        self.position = position

    def format(self, amount: int) -> str:
        if self.position == "before":
            return f"{self.symbol}{amount}"
        else:
            return f"{amount}{self.symbol}"


class QuantityFormatter:
    """Formats a quantity value with a quantity symbol."""

    def __init__(self, symbol: str = "x") -> None:
        self.symbol = symbol

    def format(self, quantity: int) -> str:
        return f"{self.symbol} {quantity}"
