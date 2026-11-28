# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    Protocol,
    TypeVar,
)

from pygame import SRCALPHA
from pygame.constants import BLEND_RGBA_MAX
from pygame.font import Font
from pygame.rect import Rect
from pygame.surface import Surface

from tuxemon.config import LOCALE_FONT_MAP
from tuxemon.constants.asset_loader import fetch_asset
from tuxemon.economy.applier import EconomyApplier
from tuxemon.economy.transaction import TransactionManager
from tuxemon.entity.npc import NPC
from tuxemon.graphics import ColorLike
from tuxemon.menu.formatter import CurrencyFormatter
from tuxemon.menu.interface import MenuItem
from tuxemon.menu.menu import Menu
from tuxemon.platform.const import buttons
from tuxemon.platform.const.graphics import (
    FONT_SIZE_ARBATA,
    FONT_SIZE_ARBATA_HAN,
    FONT_SIZE_BIGGEST,
)
from tuxemon.platform.const.sizes import MAX_BAG_MENU_ITEMS
from tuxemon.platform.events import PlayerInput
from tuxemon.sprite import Sprite
from tuxemon.ui.text import TextArea

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.economy.economy import Economy


# Same separator as the bag's page counter.
PAGE_SEPARATOR = "/"


class ShopAsset(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...


T = TypeVar("T", bound=ShopAsset)


class ShopMenuState(Menu[T], Generic[T], ABC):
    """
    A generic shop menu state that can handle any type of asset.
    All shared logic is implemented here. Subclasses provide the specific
    details for their respective asset types.
    """

    name: ClassVar[str] = "ShopMenuState"
    draw_borders = False

    def __init__(
        self,
        client: BaseClient,
        buyer: NPC,
        seller: NPC,
        economy: Economy,
        **kwargs: Any,
    ) -> None:
        # Names, prices and descriptions are set in Arbata, as in the bag.
        # Arbata only covers Latin scripts, so locales with their own font
        # (see LOCALE_FONT_MAP) keep it, at the size matching Arbata's height.
        locale = client.config.locale
        if locale.slug in LOCALE_FONT_MAP:
            self.font_filename = locale.font_file
            self.base_font_size = FONT_SIZE_ARBATA_HAN
        else:
            self.font_filename = locale.arbata_font_file
            self.base_font_size = FONT_SIZE_ARBATA
        super().__init__(client=client, **kwargs)

        # This sprite is used to display the selected asset.
        self.item_center = self.rect.width * 0.164, self.rect.height * 0.13
        self.asset_sprite = Sprite()
        self.sprites.add(self.asset_sprite)

        # Rows 10 nominal px apart: enough for Arbata's capitals and tails.
        line_pitch = self.scale_int(10)
        self.menu_items.line_spacing = line_pitch
        # One row fewer than the bag: the bag's last row may sit beside the
        # page counter, but here every row ends in a price, which would run
        # into it.
        self.page_size = MAX_BAG_MENU_ITEMS - 1
        self.current_page = 0
        self.total_pages = 0
        self.inventory: list[T] = []

        # This is the area where the asset's description is displayed.
        rect = self.client.context.rect.copy()
        rect.top = self.scale_int(103)
        rect.left = self.scale_int(3)
        rect.width = self.scale_int(250)
        # Tall enough for three lines, descenders included.
        rect.height = self.scale_int(34)
        self.text_area = TextArea(
            font=self.font,
            font_color=self.font_color,
            rect=rect,
            scaling=self.client.context.scaling,
            shadow=False,
            # Lines 10 nominal px apart too, as in the bag and journal.
            line_spacing=line_pitch - self.font.get_height(),
        )
        self.sprites.add(self.text_area, layer=100)

        self.page_number_display = TextArea(
            font=self.font,
            font_color=self.font_color,
            rect=Rect(0, 0, 1, 1),
            scaling=self.client.context.scaling,
        )
        self.sprites.add(self.page_number_display, layer=100)
        # The page counter uses the minimal font, at a size where it's crisp.
        self.page_font = Font(
            fetch_asset("font", self.client.config.locale.minimal_font_file),
            self.scale_int(FONT_SIZE_BIGGEST),
        )
        self.price_formatter = CurrencyFormatter(width=0)

        self.image_center = self.rect.width * 0.16, self.rect.height * 0.45
        self.buyer = buyer
        self.seller = seller
        self.economy = economy
        self.applier = EconomyApplier()
        self.buyer_manager = self.buyer.money_controller.money_manager
        self.seller_manager = self.seller.money_controller.money_manager
        self.transaction_manager = TransactionManager(
            self.buyer_manager, self.seller_manager, self.client.shop_manager
        )

        # The cursor is centred on each row; offset it so its middle lines up
        # with the Arbata capitals (1 nominal px above them, 2 below).
        arrow = self.cursor_controller.arrow
        row = self.font.render("H", True, self.font_color)
        caps = row.get_bounding_rect()
        arrow.y_offset = (
            caps.top
            - self.scale_int(1)
            + arrow.rect.height // 2
            - row.get_height() // 2
        )

    def calc_internal_rect(self) -> Rect:
        # The list panel's interior, in nominal pixels (same panel as the bag).
        return Rect(
            self.scale_int(96),
            self.scale_int(8),
            self.scale_int(147),
            self.scale_int(85),
        )

    def calc_menu_items_rect(self) -> Rect:
        # Rows start 2 nominal px above the panel interior (Arbata's top rows
        # are empty), with the text 8 px in so the cursor fits to its left.
        # (The shared cursor margin scales with the display scale, so the
        # list would move between scales.)
        rect = self.calc_internal_rect()
        indent = self.scale_int(8)
        return Rect(
            rect.left + indent,
            rect.top - self.scale_int(2),
            rect.width - indent,
            rect.height + self.scale_int(2),
        )

    def on_menu_selection_change(self) -> None:
        """Called when menu selection changes."""
        asset = self.get_selected_item()
        if asset:
            image = self._get_asset_image(asset)
            if image:
                self.asset_sprite.image = image
                self.asset_sprite.rect = image.get_rect(
                    center=self.image_center
                )
            self._display_asset_description(asset)

    def _add_menu_item(
        self,
        asset: T,
        label: str,
        metadata: dict[str, Any],
        unavailable: bool = False,
        price: int | None = None,
    ) -> None:
        """
        Helper to create and add a MenuItem for an asset with shared styling.

        Parameters:
            price: If given, shown at the far right of the row.
        """
        fg = self.unavailable_color_shop if unavailable else self.font_color
        image = self.font.render(label, True, fg)
        if price is not None:
            image = self._with_price(image, price, fg)
        menu_item = MenuItem(
            image, asset.name, asset.description, asset, not unavailable
        )
        menu_item.metadata.update(metadata)
        self.add(menu_item)

    def _with_price(
        self, label: Surface, price: int, fg: ColorLike
    ) -> Surface:
        """Returns the row's label with the price right-aligned after it."""
        price_image = self.font.render(
            self.price_formatter.format(price), True, fg
        )
        # Rows are drawn from the left of the list area; end the price's
        # glyphs (not the font's side bearing) 2 nominal px inside the panel,
        # level with the page counter.
        right = (
            self.calc_internal_rect().right
            - self.scale_int(2)
            - self.calc_menu_items_rect().left
        )
        ink = price_image.get_bounding_rect()
        height = max(label.get_height(), price_image.get_height())
        row = Surface((right, height), SRCALPHA)
        # MAX onto a cleared surface copies the glyphs' pixels exactly.
        row.blit(label, (0, 0), special_flags=BLEND_RGBA_MAX)
        row.blit(
            price_image, (right - ink.right, 0), special_flags=BLEND_RGBA_MAX
        )
        return row

    def update_page_number_display(self) -> None:
        internal_rect = self.calc_internal_rect()
        page_text = (
            f"{self.current_page + 1}{PAGE_SEPARATOR}{self.total_pages}"
        )
        image = self.page_font.render(page_text, True, self.font_color)
        self.page_number_display.image = image
        # Put the glyphs themselves (not the font's empty rows) 2 nominal px
        # inside the panel's bottom right corner.
        ink = image.get_bounding_rect()
        inset = self.scale_int(2)
        self.page_number_display.rect.topleft = (
            internal_rect.right - inset - ink.right,
            internal_rect.bottom - inset - ink.bottom,
        )

    def _load_page(self) -> list[T]:
        """
        Refreshes the inventory, clamps the current page to it, updates the
        page counter and returns the assets on the current page.
        """
        self.inventory = self._filter_inventory()

        if self.page_size:
            self.total_pages = max(
                1, math.ceil(len(self.inventory) / self.page_size)
            )
        else:
            self.total_pages = 1

        self.current_page = max(
            0, min(self.current_page, self.total_pages - 1)
        )
        self.update_page_number_display()

        start = self.current_page * self.page_size
        return self.inventory[start : start + self.page_size]

    @abstractmethod
    def _get_asset_image(self, asset: MenuItem[T]) -> Surface | None:
        """Returns the visual representation for the asset."""

    @abstractmethod
    def _display_asset_description(self, asset: MenuItem[T]) -> None:
        """Displays the description for the asset."""

    @abstractmethod
    def _filter_inventory(self) -> list[T]:
        """Returns the filtered list of assets for the shop."""

    @abstractmethod
    def _populate_menu(self, inventory: list[T]) -> None:
        """Populates the menu with assets based on a provided inventory list."""

    @abstractmethod
    def _get_selection_menu_params(
        self, menu_item: MenuItem[T]
    ) -> dict[str, Any]:
        """Provides parameters for the transaction menu."""

    def initialize_items(self) -> Generator[MenuItem[T], None, None]:
        paged_inventory = self._load_page()
        if not paged_inventory:
            return

        self._populate_menu(paged_inventory)
        yield from self.menu_items

    def reload_shop(self) -> None:
        self.clear()
        self._populate_menu(self._load_page())
        self.selected_index = (
            min(self.selected_index, len(self.menu_items) - 1)
            if self.menu_items
            else -1
        )
        self.on_menu_selection_change()

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        total_pages = self.total_pages

        if event.button == buttons.RIGHT and event.pressed:
            if self.current_page < total_pages - 1:
                self.current_page += 1
                self.reload_shop()
            return None
        elif event.button == buttons.LEFT and event.pressed:
            if self.current_page > 0:
                self.current_page -= 1
                self.reload_shop()
            return None

        return super().process_event(event)

    def on_menu_selection(self, menu_item: MenuItem[T]) -> None:
        """Handles the common logic for pushing the quantity menu."""
        params = self._get_selection_menu_params(menu_item)

        self.client.state_manager.push_state(
            "QuantityPickerState",
            client=self.client,
            min_value=1,
            max_value=params["max_quantity"],
            start_value=1,
            step=1,
            callback=params["callback"],
            cost=params["cost"],
            wallet_money=params.get("wallet_money"),
        )
