# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass
class Investment:
    symbol: str
    shares: int
    purchase_price: float


class PortfolioManager:
    """Manages an NPC's investment portfolio."""

    def __init__(self) -> None:
        self.investments: dict[str, Investment] = {}

    def buy_shares(self, symbol: str, shares: int, price: float) -> float:
        """Buys shares of an investment and returns the total cost."""
        if not symbol.isalnum():
            raise ValueError("Invalid symbol format.")

        if shares <= 0 or price <= 0:
            raise ValueError("Shares and price must be positive.")

        total_cost = shares * price
        if symbol in self.investments:
            current = self.investments[symbol]
            new_shares = current.shares + shares
            new_purchase_price = (
                (current.shares * current.purchase_price) + total_cost
            ) / new_shares
            current.shares = new_shares
            current.purchase_price = new_purchase_price
        else:
            self.investments[symbol] = Investment(
                symbol=symbol, shares=shares, purchase_price=price
            )
        return total_cost

    def sell_shares(self, symbol: str, shares: int, price: float) -> float:
        """Sells shares of an investment and returns the total revenue."""
        if not symbol.isalnum():
            raise ValueError("Invalid symbol format.")

        if symbol not in self.investments:
            raise KeyError(f"No such investment: {symbol}")
        if shares <= 0:
            raise ValueError("Shares must be positive.")

        investment = self.investments[symbol]
        if shares > investment.shares:
            raise ValueError("Insufficient shares to sell.")

        total_revenue = shares * price
        investment.shares -= shares
        if investment.shares == 0:
            del self.investments[symbol]
        return total_revenue

    def get_portfolio_value(self, market_prices: Mapping[str, float]) -> float:
        """Calculates the total market value of the portfolio."""
        total_value = 0.0
        for symbol, investment in self.investments.items():
            if symbol in market_prices:
                total_value += investment.shares * market_prices[symbol]
        return total_value

    def get_state(self) -> dict[str, Any]:
        """Returns a savable state of the portfolio."""
        return {
            "investments": [
                {
                    "symbol": inv.symbol,
                    "shares": inv.shares,
                    "purchase_price": inv.purchase_price,
                }
                for inv in self.investments.values()
            ]
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> PortfolioManager:
        """Recreates a PortfolioManager from a saved state."""
        manager = cls()
        if "investments" in state:
            for inv_data in state["investments"]:
                manager.investments[inv_data["symbol"]] = Investment(
                    symbol=inv_data["symbol"],
                    shares=inv_data["shares"],
                    purchase_price=inv_data["purchase_price"],
                )
        return manager


class MarketDataManager:
    def __init__(self):
        self.prices: dict[str, float] = {}

    def get_price(self, symbol: str) -> float:
        """Returns the current market price of the given symbol, or 0.0 if unavailable."""
        return self.prices.get(symbol, 0.0)

    def update_prices(self, price_map: dict[str, float]) -> None:
        """Updates market prices for multiple symbols using the provided price map."""
        for symbol, price in price_map.items():
            self.set_price(symbol, price)

    def set_price(self, symbol: str, price: float) -> None:
        """Sets the market price for the given symbol if the price is positive and the symbol is valid."""
        if not symbol.isalnum():
            raise ValueError("Invalid symbol format.")

        if price > 0:
            self.prices[symbol] = price
        else:
            raise ValueError("Price must be positive.")

    def apply_fluctuation(self, symbol: str, percentage_change: float) -> None:
        """Changes the price of a symbol by a percentage."""
        if not symbol.isalnum():
            raise ValueError("Invalid symbol format.")

        current_price = self.get_price(symbol)
        if current_price > 0:
            new_price = current_price * (1 + percentage_change)
            self.set_price(symbol, new_price)


# Example usage:
# market = MarketDataManager()
# market.set_price("GGL", 1500.0)
# market.apply_fluctuation("GGL", 0.05) # 5% increase
# print(market.get_price("GGL")) # Output: 1575.0

# class MoneyManager:
#     def __init__(self) -> None:
#         self.portfolio_manager: PortfolioManager = PortfolioManager()

#     def get_total_wealth(self, market_prices: Mapping[str, float]) -> int:
#         portfolio_value = self.portfolio_manager.get_portfolio_value(market_prices)
#         return int(self.money + self.bank_account + portfolio_value)

#     def buy_investment(self, symbol: str, shares: int, price: float) -> None:
#         """Buys investment shares using money from the bank account."""
#         total_cost = self.portfolio_manager.buy_shares(symbol, shares, price)
#         self.withdraw_from_bank(int(total_cost))

#     def sell_investment(self, symbol: str, shares: int, price: float) -> None:
#         """Sells investment shares and deposits the revenue into the bank account."""
#         total_revenue = self.portfolio_manager.sell_shares(symbol, shares, price)
#         self.deposit_to_bank(int(total_revenue))

# def decode_money(json_data: Mapping[str, Any]) -> MoneyManager:
#       for bill_name, bill_data in bills.items():
#         portfolio_data = json_data.get("portfolio", {})
#         money_manager.portfolio_manager = PortfolioManager.from_state(portfolio_data)

# def encode_money(money_manager: MoneyManager) -> Mapping[str, Any]:
#         "portfolio": money_manager.portfolio_manager.get_state(),
