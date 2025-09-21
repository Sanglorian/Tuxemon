# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from functools import partial
from typing import Any, ClassVar, Optional

from pygame.surface import Surface

from tuxemon.item.shop_utils import filter_party
from tuxemon.locale import T
from tuxemon.menu.interface import MenuItem
from tuxemon.menu.quantity import QuantityAndCostMenu
from tuxemon.monster import Monster
from tuxemon.session import local_session
from tuxemon.states.shop_base import ShopMenuState


class HealingCostMenu(QuantityAndCostMenu):
    name: ClassVar[str] = "HealingCostMenu"

    def __init__(
        self,
        healer_state: ShopHealingMenuState,
        monster: Monster,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self._healer_state = healer_state
        self._monster = monster

    def calculate_total(self, _: int) -> int:
        return self._healer_state.base_healing_cost * self.quantity


class ShopHealingMenuState(ShopMenuState[Monster]):
    name: ClassVar[str] = "ShopHealingMenuState"

    def __init__(
        self, *args: Any, base_healing_cost: int = 5, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.base_healing_cost = base_healing_cost

    def _get_asset_image(self, asset: MenuItem[Monster]) -> Optional[Surface]:
        image = asset.game_object.get_sprite("front")
        return image.image if image else None

    def _display_asset_description(self, asset: MenuItem[Monster]) -> None:
        if asset.description:
            self.dialog.alert(asset.description, dialog_speed="max")

    def _filter_inventory(self) -> list[Monster]:
        return filter_party(self.buyer, self.seller, self.economy)

    def _populate_menu(self, inventory: list[Monster]) -> None:
        for monster in inventory:
            if monster.hp_ratio == 1.0:
                continue  # Already fully healed

            cost = self._calculate_healing_cost(monster)
            label = self._format_monster_label(monster, cost)
            unavailable = cost > self.seller_manager.get_money()
            self._add_menu_item(monster, label, {"cost": cost}, unavailable)

    def _get_selection_menu_params(
        self, menu_item: MenuItem[Monster]
    ) -> dict[str, Any]:
        monster = menu_item.game_object
        missing_hp = monster.hp - monster.current_hp
        available_money = self.seller_manager.get_money()

        max_affordable_hp = available_money // self.base_healing_cost
        max_quantity = min(missing_hp, max_affordable_hp)

        def heal_monster(quantity: int) -> None:
            quantity = min(quantity, missing_hp)
            cost = quantity * self.base_healing_cost
            if quantity > 0 and cost <= available_money:
                self.seller_manager.remove_money(cost)
                monster.current_hp += quantity
                monster.status.clear_status(local_session)
                self.reload_shop()

        return {
            "callback": partial(heal_monster),
            "max_quantity": max_quantity,
            "cost": self.base_healing_cost,
        }

    def _calculate_healing_cost(self, monster: Monster) -> int:
        missing_hp = monster.hp - monster.current_hp
        return missing_hp * self.base_healing_cost

    def _format_monster_label(self, monster: Monster, cost: int) -> str:
        return f"{monster.name} HP: {monster.current_hp}/{monster.hp}"

    def on_menu_selection(self, menu_monster: MenuItem[Monster]) -> None:
        monster = menu_monster.game_object
        params = self._get_selection_menu_params(menu_monster)

        menu = HealingCostMenu(
            healer_state=self,
            monster=monster,
            callback=params["callback"],
            max_quantity=params["max_quantity"],
            quantity=1,
            shrink_to_items=True,
            cost=0,  # ignored, overridden by calculate_total
            label=lambda q: T.format(
                "shop_heal_to", {"hp": min(monster.current_hp + q, monster.hp)}
            ),
        )

        self.client.state_manager.push_state(menu)
