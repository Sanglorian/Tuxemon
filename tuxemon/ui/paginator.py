# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import math
from typing import Any


class Paginator:
    def __init__(self, items: list[Any], page_size: int):
        """
        Initializes a Paginator instance with a list of items and a page size.
        """
        if not isinstance(page_size, int) or page_size <= 0:
            raise ValueError("Page size must be a positive integer.")
        self._items: list[Any] = items
        self._page_size: int = page_size
        self._total_items: int = len(items)
        self._total_pages: int = (
            math.ceil(self._total_items / self._page_size)
            if self._page_size > 0
            else 0
        )

    def paginate(self, page_number: int) -> list[Any]:
        """
        Paginates the list of items based on the page size and page number.
        """
        if page_number < 0 or page_number >= self._total_pages:
            return []
        start = page_number * self._page_size
        end = start + self._page_size
        return self._items[start:end]

    def total_pages(self) -> int:
        """
        Calculates the total number of pages required for the list of items.
        """
        return self._total_pages

    def calculate_page_data(self, current_page: int) -> tuple[int, list[Any]]:
        """
        Calculates both the total number of pages and the items for the current page.
        """
        total_pages = self.total_pages()
        page_items = self.paginate(current_page)
        return total_pages, page_items

    def update_items(self, new_items: list[Any]) -> None:
        """
        Updates the internal list of items and recalculates pagination metadata.
        """
        self._items = new_items
        self._total_items = len(new_items)
        self._total_pages = (
            math.ceil(self._total_items / self._page_size)
            if self._page_size > 0
            else 0
        )
