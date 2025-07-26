# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import math
import unittest

from tuxemon.ui.paginator import Paginator


class TestPaginator(unittest.TestCase):

    def setUp(self) -> None:
        self.items = [1, 2, 3, 4, 5]
        self.page_size = 2
        self.paginator = Paginator(self.items, self.page_size)

    def test_init(self):
        self.assertEqual(self.paginator._items, self.items)
        self.assertEqual(self.paginator._page_size, self.page_size)
        self.assertEqual(self.paginator._total_items, len(self.items))
        self.assertEqual(
            self.paginator._total_pages,
            math.ceil(len(self.items) / self.page_size),
        )

    def test_init_invalid_page_size(self):
        page_size = 0
        with self.assertRaises(ValueError):
            Paginator(self.items, page_size)

    def test_init_invalid_page_size_negative(self):
        page_size = -1
        with self.assertRaises(ValueError):
            Paginator(self.items, page_size)

    def test_init_invalid_page_size_non_integer(self):
        page_size = 2.5
        with self.assertRaises(ValueError):
            Paginator(self.items, page_size)

    def test_paginate(self):
        self.assertEqual(self.paginator.paginate(0), [1, 2])
        self.assertEqual(self.paginator.paginate(1), [3, 4])
        self.assertEqual(self.paginator.paginate(2), [5])

    def test_paginate_out_of_range(self):
        self.assertEqual(self.paginator.paginate(-1), [])
        self.assertEqual(self.paginator.paginate(3), [])

    def test_total_pages(self):
        self.assertEqual(
            self.paginator.total_pages(),
            math.ceil(len(self.items) / self.page_size),
        )

    def test_calculate_page_data(self):
        total_pages, page_items = self.paginator.calculate_page_data(0)
        self.assertEqual(
            total_pages, math.ceil(len(self.items) / self.page_size)
        )
        self.assertEqual(page_items, [1, 2])

    def test_empty_list(self):
        items = []
        paginator = Paginator(items, self.page_size)
        self.assertEqual(paginator.total_pages(), 0)
        self.assertEqual(paginator.paginate(0), [])

    def test_page_size_of_1(self):
        page_size = 1
        paginator = Paginator(self.items, page_size)
        self.assertEqual(paginator.total_pages(), len(self.items))
        self.assertEqual(paginator.paginate(0), [1])
        self.assertEqual(paginator.paginate(1), [2])
        self.assertEqual(paginator.paginate(2), [3])
        self.assertEqual(paginator.paginate(3), [4])
        self.assertEqual(paginator.paginate(4), [5])

    def test_page_size_equal_to_total_items(self):
        page_size = len(self.items)
        paginator = Paginator(self.items, page_size)
        self.assertEqual(paginator.total_pages(), 1)
        self.assertEqual(paginator.paginate(0), self.items)

    def test_page_number_of_0(self):
        self.assertEqual(self.paginator.paginate(0), [1, 2])

    def test_page_number_equal_to_total_pages(self):
        self.assertEqual(
            self.paginator.paginate(self.paginator.total_pages()), []
        )

    def test_negative_page_number(self):
        self.assertEqual(self.paginator.paginate(-1), [])

    def test_non_integer_page_number(self):
        with self.assertRaises(TypeError):
            self.paginator.paginate(1.5)

    def test_page_size_of_0(self):
        page_size = 0
        with self.assertRaises(ValueError):
            Paginator(self.items, page_size)

    def test_page_size_is_very_large(self):
        page_size = 100
        paginator = Paginator(self.items, page_size)
        self.assertEqual(paginator.total_pages(), 1)
        self.assertEqual(paginator.paginate(0), self.items)

    def test_update_items(self):
        new_items = [10, 20, 30, 40, 50, 60]
        self.paginator.update_items(new_items)
        total_pages = self.paginator.total_pages()
        self.assertEqual(total_pages, 3)
        self.assertEqual(self.paginator.paginate(2), [50, 60])

    def test_update_to_empty_list(self):
        self.paginator.update_items([])
        self.assertEqual(self.paginator.total_pages(), 0)
        self.assertEqual(self.paginator.paginate(0), [])

    def test_paginate_with_invalid_page_number(self):
        self.assertEqual(self.paginator.paginate(-1), [])
        self.assertEqual(self.paginator.paginate(99), [])

    def test_zero_items_initially(self):
        paginator = Paginator([], self.page_size)
        self.assertEqual(paginator.total_pages(), 0)
        self.assertEqual(paginator.paginate(0), [])

    def test_invalid_page_size(self):
        with self.assertRaises(ValueError):
            Paginator(self.items, 0)
        with self.assertRaises(ValueError):
            Paginator(self.items, -3)
        with self.assertRaises(ValueError):
            Paginator(self.items, "two")
