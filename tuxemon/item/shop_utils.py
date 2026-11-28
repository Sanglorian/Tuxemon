# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from typing import TYPE_CHECKING

from tuxemon.item.item import Item
from tuxemon.item.stock import INFINITE_ITEMS
from tuxemon.locale.locale import T
from tuxemon.monster.monster import Monster

if TYPE_CHECKING:
    from tuxemon.economy.economy import Economy


def get_item_label(item: Item, qty: int, seller_mode: bool) -> str:
    is_infinite = item.quantity == INFINITE_ITEMS

    if seller_mode:
        return (
            item.name if is_infinite else f"{item.name} x {item.quantity}"
        )

    if is_infinite:
        return item.name
    elif qty > 0:
        return f"{item.name} x {qty}"
    else:
        return T.translate("shop_buy_soldout")


def get_monster_label(monster: Monster) -> str:
    return f"lv.{monster.level} {monster.name}"


def generate_label(
    entity: Item | Monster,
    economy: Economy,
    qty: int | None = None,
    seller_mode: bool = False,
) -> tuple[str, str, int]:
    """
    Build a display label for an Item or Monster. The label leaves out the
    price, which shops show separately.

    Returns:
        (label, discount_label, unit_price)
    """
    qty = qty or 1
    safe_qty = qty if qty > 0 else 1

    price = economy.calculate_price(entity, qty, seller_mode)
    unit_price = (
        round(price.final_price / safe_qty)
        if qty != -1
        else round(price.final_price)
    )
    discount_label = (
        f" ({price.modifier_percent}% off)"
        if price.modifier_percent > 0
        else ""
    )

    if isinstance(entity, Item):
        label = get_item_label(entity, qty, seller_mode)
    elif isinstance(entity, Monster):
        label = get_monster_label(entity)

    return label, discount_label, unit_price
