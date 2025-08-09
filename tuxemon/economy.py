# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from tuxemon.db import EconomyItemModel, EconomyModel, db
from tuxemon.item.item import Item
from tuxemon.monster import Monster
from tuxemon.prepare import GRAD_BLUE

if TYPE_CHECKING:
    from tuxemon.npc import NPC
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


@dataclass
class ShopInventory:
    items: list[Item] = field(default_factory=list)
    monsters: list[Monster] = field(default_factory=list)

    def has_item(self, slug: str) -> bool:
        return any(item.slug == slug for item in self.items)

    def has_monster(self, slug: str) -> bool:
        return any(monster.slug == slug for monster in self.monsters)


class Economy:
    """
    Represents an economy's data in the game, containing items and monsters definitions
    with their associated prices, costs, and initial inventory values.
    It provides methods for looking up and updating these definitions.
    """

    def __init__(self, slug: Optional[str] = None) -> None:
        self.model: EconomyModel

        if slug:
            self.load(slug)
        else:
            self.model = EconomyModel(
                slug="",
                resale_multiplier=0.0,
                background=GRAD_BLUE,
                items=[],
                monsters=[],
            )
            logger.warning(
                "Economy initialized without a slug. It's an empty economy."
            )

    def load(self, slug: str) -> None:
        """
        Loads the economy from the database based on the given slug.

        Parameters:
            slug: The slug of the economy to load.

        Raises:
            RuntimeError: If the economy with the given slug is not found
            in the database.
        """
        try:
            results = EconomyModel.lookup(slug, db)
            self.model = results
        except Exception as e:
            logger.error(f"Failed to load economy '{slug}': {e}")
            raise RuntimeError(
                f"Economy with slug '{slug}' not found in database."
            ) from e

    def lookup_item_field(self, item_slug: str, field: str) -> Optional[int]:
        """
        Looks up the value of a field for an item definition in the economy.

        Parameters:
            item_slug: The slug of the item definition to look up.
            field: The field to look up (e.g., "price", "cost", "inventory").

        Returns:
            The value of the field if found, otherwise None.
        """
        item = next(
            (item for item in self.model.items if item.name == item_slug),
            None,
        )
        if item and hasattr(item, field):
            return int(getattr(item, field))
        return None

    def lookup_item(self, item_slug: str, field: str) -> Optional[int]:
        """
        Looks up the value of a field for an item definition in the economy.
        This is an alias for lookup_item_field.

        Parameters:
            item_slug: The slug of the item definition to look up.
            field: The field to look up.

        Returns:
            The value of the field or None.
        """
        return self.lookup_item_field(item_slug, field)

    def lookup_item_price(self, item_slug: str) -> int:
        """
        Looks up the price of an item definition in the economy.

        Parameters:
            item_slug: The slug of the item definition to look up.

        Returns:
            The price of the item.

        Raises:
            RuntimeError: If the item definition is not found in the economy.
        """
        value = self.lookup_item(item_slug, "price")
        if value is None:
            raise RuntimeError(
                f"Item '{item_slug}' has no price defined in economy '{self.model.slug}'"
            )
        return value

    def lookup_item_cost(self, item_slug: str) -> int:
        """
        Looks up the cost of an item definition in the economy.

        Parameters:
            item_slug: The slug of the item definition to look up.

        Returns:
            The cost of the item.

        Raises:
            RuntimeError: If the item definition is not found in the economy.
        """
        value = self.lookup_item(item_slug, "cost")
        if value is None:
            raise RuntimeError(
                f"Item '{item_slug}' has no cost defined in economy '{self.model.slug}'"
            )
        return value

    def lookup_item_inventory(self, item_slug: str) -> int:
        """
        Looks up the initial inventory quantity of an item definition in the economy.
        This represents the default quantity specified in the economy data.

        Parameters:
            item_slug: The slug of the item definition to look up.

        Returns:
            The initial inventory quantity of the item.

        Raises:
            RuntimeError: If the item definition is not found in the economy.
        """
        value = self.lookup_item(item_slug, "inventory")
        if value is None:
            raise RuntimeError(
                f"Item '{item_slug}' has no inventory defined in economy '{self.model.slug}'"
            )
        return value

    def update_item_quantity(self, item_slug: str, quantity: int) -> None:
        """
        Updates the inventory quantity field of an item definition within this economy.
        This primarily affects the data model for the economy itself, not
        an NPC's actual inventory.

        Parameters:
            item_slug: The slug of the item definition to update.
            quantity: The new quantity for the item definition.
        """
        self.update_item_field(item_slug, "inventory", quantity)

    def get_item(self, item_slug: str) -> Optional[EconomyItemModel]:
        """
        Gets an EconomyItemModel definition from the economy by its slug.

        Parameters:
            item_slug: The slug of the item definition to get.

        Returns:
            The EconomyItemModel if found, otherwise None.
        """
        return next(
            (item for item in self.model.items if item.name == item_slug),
            None,
        )

    def get_item_field(self, item_slug: str, field: str) -> Optional[int]:
        """
        Gets the value of a field for an item definition in the economy.
        This is an alias for lookup_item_field.

        Parameters:
            item_slug: The slug of the item definition to get.
            field: The field to get.

        Returns:
            The value of the field if found, otherwise None.
        """
        return self.lookup_item_field(item_slug, field)

    def update_item_field(
        self, item_slug: str, field: str, value: int
    ) -> None:
        """
        Updates the value of a specific field for an item definition in the economy.

        Parameters:
            item_slug: The slug of the item definition to update.
            field: The field to update.
            value: The new value of the field.

        Raises:
            RuntimeError: If the item definition is not found in the economy.
        """
        item = self.get_item(item_slug)
        if item:
            if hasattr(item, field):
                setattr(item, field, value)
            else:
                raise AttributeError(
                    f"Item definition '{item_slug}' has no field '{field}'"
                )
        else:
            raise RuntimeError(
                f"Item definition '{item_slug}' not found in economy '{self.model.slug}'"
            )

    def get_monster_field(
        self, monster_name: str, field: str
    ) -> Optional[int]:
        """
        Gets the value of a field for a monster definition in the economy.

        Parameters:
            monster_name: The name of the monster definition to get.
            field: The field to get (e.g., "level", "inventory").

        Returns:
            The value of the field if found, otherwise None.
        """
        monster = next(
            (
                monster
                for monster in self.model.monsters
                if monster.name == monster_name
            ),
            None,
        )
        if monster and hasattr(monster, field):
            return int(getattr(monster, field))
        return None

    def variable(
        self, variables: Sequence[dict[str, str]], character: NPC
    ) -> bool:
        """
        Checks if the given variables (conditions from economy data) match
        the character's game variables.

        Parameters:
            variables: A sequence of dictionaries, each representing a set of
                variable-value pairs to check.
            character: The character (NPC or player) whose game variables are
                checked.

        Returns:
            True if all specified variable conditions match the character's
            game variables, otherwise False.
        """
        return all(
            all(
                character.game_variables.get(key) == value
                for key, value in variable.items()
            )
            for variable in variables
        )


class EconomyApplier:
    """
    Manages the application of an Economy's definitions to a character (e.g., NPC),
    creating actual game entities (Items, Monsters) and populating their inventories
    based on economy data and character game variables.
    """

    def apply_economy_to_character(
        self, session: Session, economy: Economy, character: NPC
    ) -> None:
        """
        Applies economy-defined items and monsters to a character, populating a separate
        shop inventory based on the player's game variables and availability conditions.
        """
        player = session.player
        shop_items = []
        shop_monsters = []

        # Process items
        for eco_item_model in economy.model.items:
            label = f"{economy.model.slug}:{eco_item_model.name}"

            if label not in player.game_variables:
                initial_quantity = economy.lookup_item_inventory(
                    eco_item_model.name
                )
                player.game_variables[label] = initial_quantity

            if eco_item_model.variables and not economy.variable(
                eco_item_model.variables, player
            ):
                logger.debug(f"Skipping item '{eco_item_model.name}'")
                continue

            try:
                item_instance = Item.create(eco_item_model.name)
                item_instance.set_quantity(int(player.game_variables[label]))
                shop_items.append(item_instance)
            except Exception as e:
                logger.error(
                    f"Could not create Item '{eco_item_model.name}': {e}"
                )

        # Process monsters
        for eco_monster_model in economy.model.monsters:
            label = f"{economy.model.slug}:{eco_monster_model.name}"

            if label not in player.game_variables:
                default = (
                    economy.get_monster_field(
                        eco_monster_model.name, "inventory"
                    )
                    or 1
                )
                player.game_variables[label] = default

            if eco_monster_model.variables and not economy.variable(
                eco_monster_model.variables, player
            ):
                logger.debug(f"Skipping monster '{eco_monster_model.name}'")
                continue

            try:
                monster_instance = Monster.create(eco_monster_model.name)
                monster_instance.level = eco_monster_model.level
                monster_instance.current_hp = monster_instance.hp
                shop_monsters.append(monster_instance)
            except Exception as e:
                logger.error(
                    f"Could not create Monster '{eco_monster_model.name}': {e}"
                )

        character.shop_inventory = ShopInventory(
            items=shop_items, monsters=shop_monsters
        )
        logger.info(
            f"Shop inventory set for '{character.slug}' with {len(shop_items)} items and {len(shop_monsters)} monsters."
        )
