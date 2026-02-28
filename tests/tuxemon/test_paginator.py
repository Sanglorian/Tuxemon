# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import math

import pytest

from tuxemon.ui.paginator import Paginator


@pytest.fixture
def items():
    return [1, 2, 3, 4, 5]


@pytest.fixture
def page_size():
    return 2


@pytest.fixture
def paginator(items, page_size):
    return Paginator(items, page_size)


def test_init(paginator, items, page_size):
    assert paginator._items == items
    assert paginator._page_size == page_size
    assert paginator._total_items == len(items)
    assert paginator._total_pages == math.ceil(len(items) / page_size)


@pytest.mark.parametrize("bad_size", [0, -1, 2.5])
def test_init_invalid_page_size(items, bad_size):
    with pytest.raises(ValueError):
        Paginator(items, bad_size)


def test_paginate(paginator):
    assert paginator.paginate(0) == [1, 2]
    assert paginator.paginate(1) == [3, 4]
    assert paginator.paginate(2) == [5]


def test_paginate_out_of_range(paginator):
    assert paginator.paginate(-1) == []
    assert paginator.paginate(3) == []


def test_total_pages(paginator, items, page_size):
    assert paginator.total_pages() == math.ceil(len(items) / page_size)


def test_calculate_page_data(paginator, items, page_size):
    total_pages, page_items = paginator.calculate_page_data(0)
    assert total_pages == math.ceil(len(items) / page_size)
    assert page_items == [1, 2]


def test_empty_list(page_size):
    paginator = Paginator([], page_size)
    assert paginator.total_pages() == 0
    assert paginator.paginate(0) == []


def test_page_size_of_1(items):
    paginator = Paginator(items, 1)
    assert paginator.total_pages() == len(items)
    assert paginator.paginate(0) == [1]
    assert paginator.paginate(1) == [2]
    assert paginator.paginate(2) == [3]
    assert paginator.paginate(3) == [4]
    assert paginator.paginate(4) == [5]


def test_page_size_equal_to_total_items(items):
    paginator = Paginator(items, len(items))
    assert paginator.total_pages() == 1
    assert paginator.paginate(0) == items


def test_page_number_of_0(paginator):
    assert paginator.paginate(0) == [1, 2]


def test_page_number_equal_to_total_pages(paginator):
    assert paginator.paginate(paginator.total_pages()) == []


def test_negative_page_number(paginator):
    assert paginator.paginate(-1) == []


def test_non_integer_page_number(paginator):
    with pytest.raises(TypeError):
        paginator.paginate(1.5)


def test_page_size_is_very_large(items):
    paginator = Paginator(items, 100)
    assert paginator.total_pages() == 1
    assert paginator.paginate(0) == items


def test_update_items(paginator):
    new_items = [10, 20, 30, 40, 50, 60]
    paginator.update_items(new_items)
    assert paginator.total_pages() == 3
    assert paginator.paginate(2) == [50, 60]


def test_update_to_empty_list(paginator):
    paginator.update_items([])
    assert paginator.total_pages() == 0
    assert paginator.paginate(0) == []


def test_paginate_with_invalid_page_number(paginator):
    assert paginator.paginate(-1) == []
    assert paginator.paginate(99) == []


def test_zero_items_initially(page_size):
    paginator = Paginator([], page_size)
    assert paginator.total_pages() == 0
    assert paginator.paginate(0) == []


@pytest.mark.parametrize("bad_size", [0, -3, "two"])
def test_invalid_page_size(items, bad_size):
    with pytest.raises(ValueError):
        Paginator(items, bad_size)
