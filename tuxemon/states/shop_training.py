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
from tuxemon.prepare import MAX_LEVEL
from tuxemon.states.shop_base import ShopMenuState


class TrainingCostMenu(QuantityAndCostMenu):
    name: ClassVar[str] = "TrainingCostMenu"

    def __init__(
        self,
        trainer_state: ShopTrainingMenuState,
        monster: Monster,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self._trainer_state = trainer_state
        self._monster = monster

    def calculate_total(self, _: int) -> int:
        return self._trainer_state._calculate_total_training_cost(
            self._monster, self.quantity
        )


class ShopTrainingMenuState(ShopMenuState[Monster]):
    """
    A specific shop state for a training service, inheriting from the generic
    ShopMenuState. This state allows the player to pay to level up their monsters.
    """

    name: ClassVar[str] = "ShopTrainingMenuState"

    def __init__(
        self, *args: Any, base_training_cost: int = 100, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.base_training_cost = base_training_cost

    def _get_asset_image(self, asset: MenuItem[Monster]) -> Optional[Surface]:
        """Returns the front sprite image for a monster."""
        image = asset.game_object.get_sprite("front")
        return image.image if image else None

    def _display_asset_description(self, asset: MenuItem[Monster]) -> None:
        """Displays the monster's description."""
        if asset.description:
            self.dialog.alert(asset.description, dialog_speed="max")

    def _filter_inventory(self) -> list[Monster]:
        """
        The training shop's inventory is the player's own party.
        """
        return filter_party(self.buyer, self.seller, self.economy)

    def _populate_menu(self, inventory: list[Monster]) -> None:
        """Populates the menu with the player's monsters and their training costs."""
        for monster in inventory:
            if monster.level >= MAX_LEVEL:
                continue  # Skip monsters already at max level

            cost = self._calculate_training_cost(monster)
            label = self._format_monster_label(monster, cost)
            unavailable = (
                cost > self.seller_manager.get_money() or monster.is_fainted
            )
            self._add_menu_item(monster, label, {"cost": cost}, unavailable)

    def _get_selection_menu_params(
        self, menu_item: MenuItem[Monster]
    ) -> dict[str, Any]:
        monster = menu_item.game_object
        available_money = self.seller_manager.get_money()

        if monster.level >= MAX_LEVEL:
            return {
                "callback": lambda quantity: None,
                "max_quantity": 0,
                "cost": 0,
            }

        total_cost = 0
        max_quantity = 0
        for i in range(1, MAX_LEVEL - monster.level + 1):
            level_cost = self._get_level_cost(monster, monster.level + i)
            if total_cost + level_cost > available_money:
                break
            total_cost += level_cost
            max_quantity = i

        def train_monster(quantity: int) -> None:
            quantity = min(quantity, MAX_LEVEL - monster.level)
            cost = self._calculate_total_training_cost(monster, quantity)
            if quantity > 0 and cost <= available_money:
                self.seller_manager.remove_money(cost)
                monster.set_level(monster.level + quantity)
                monster.moves.update_moves(
                    monster.level, quantity, monster.stage
                )
                self.reload_shop()

        base_cost = self._calculate_training_cost(monster)
        return {
            "callback": partial(train_monster),
            "max_quantity": max_quantity,
            "cost": base_cost,
        }

    def _calculate_total_training_cost(
        self, monster: Monster, quantity: int
    ) -> int:
        return sum(
            (monster.level + i) * self.base_training_cost
            for i in range(1, quantity + 1)
        )

    def _get_level_cost(self, monster: Monster, target_level: int) -> int:
        return target_level * self.base_training_cost  # Default linear scaling

    def _format_monster_label(self, monster: Monster, cost: int) -> str:
        return f"{monster.name} Lv.{monster.level} (${cost})"

    def _calculate_training_cost(self, monster: Monster) -> int:
        """Calculates the cost to level up a monster."""
        return (monster.level + 1) * self.base_training_cost

    def on_menu_selection(self, menu_monster: MenuItem[Monster]) -> None:
        monster = menu_monster.game_object
        params = self._get_selection_menu_params(menu_monster)

        menu = TrainingCostMenu(
            trainer_state=self,
            monster=monster,
            callback=params["callback"],
            max_quantity=params["max_quantity"],
            quantity=1,
            shrink_to_items=True,
            cost=0,  # ignored
            label=lambda q: T.format(
                "shop_train_to", {"level": monster.level + q}
            ),
        )

        self.client.state_manager.push_state(menu)
