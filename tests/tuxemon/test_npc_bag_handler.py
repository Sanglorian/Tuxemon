# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from tuxemon.entity_dir.bag import BagHandler
from tuxemon.item.item import Item


@pytest.fixture
def item():
    itm = Item.test()
    itm.slug = "test_item"
    return itm


@pytest.fixture
def handler():
    return BagHandler(item_boxes=MagicMock(), owner=MagicMock())


@pytest.fixture
def two_items():
    a = Item.test()
    a.slug = "item1"
    b = Item.test()
    b.slug = "item2"
    return a, b


def test_init(handler):
    assert handler._items == []
    assert handler._bag_limit == 99


def test_add_item(handler, item):
    handler.add_item(item)
    assert item in handler._items


def test_add_item_to_locker(handler, item):
    handler._bag_limit = 0
    handler.add_item(item)
    assert handler._items == []


@pytest.mark.parametrize(
    "qty1, qty2, expected",
    [
        (1, 5, 6),
        (0, 0, 0),
        (3, 0, 3),
    ],
)
def test_add_item_existing(handler, item, qty1, qty2, expected):
    handler.add_item(item, quantity=qty1)
    handler.add_item(item, quantity=qty2)
    assert handler.find_item("test_item").quantity == expected


def test_remove_item(handler, item):
    handler.add_item(item)
    handler.remove_item(item)
    assert item not in handler._items


def test_remove_item_with_quantity(handler, item):
    handler.add_item(item, quantity=10)
    handler.remove_item(item, quantity=5)
    assert handler.find_item("test_item").quantity == 5


def test_remove_item_below_zero(handler, item):
    handler.add_item(item, quantity=10)
    handler.remove_item(item, quantity=15)
    assert item not in handler._items


def test_remove_item_zero_quantity(handler, item):
    handler.add_item(item, quantity=10)
    handler.remove_item(item, quantity=0)
    assert handler.find_item("test_item").quantity == 10


def test_find_item(handler, item):
    handler.add_item(item)
    assert handler.find_item("test_item") is item


def test_find_item_not_found(handler):
    assert handler.find_item("test_item") is None


def test_find_item_by_id(handler, item):
    handler.add_item(item)
    assert handler.find_item_by_id(item.instance_id) is item


def test_find_item_by_id_not_found(handler):
    assert handler.find_item_by_id(uuid4()) is None


def test_get_items(handler):
    a = Item.test()
    a.slug = "a"
    b = Item.test()
    b.slug = "b"
    handler.add_item(a)
    handler.add_item(b)
    assert a in handler.items and b in handler.items


def test_clear_items(handler, item):
    handler.add_item(item)
    handler.clear_items()
    assert handler._items == []


def test_swap_items_success(handler, two_items):
    a, b = two_items
    handler.add_item(a)
    handler.add_item(b)
    handler.swap_items(0, 1)
    assert handler.items == [b, a]


def test_swap_items_out_of_bounds(handler, item):
    handler.add_item(item)
    with pytest.raises(IndexError):
        handler.swap_items(0, 5)


def test_add_item_at_limit_routes_to_box(handler, item):
    handler._bag_limit = 1
    handler.add_item(item)

    item2 = Item.test()
    item2.slug = "different_item"
    handler.add_item(item2)

    assert item2 not in handler.items
    handler._item_boxes.add_item.assert_called()


def test_get_all_item_quantities(handler, item):
    handler.add_item(item, quantity=5)

    item2 = Item.test()
    item2.slug = "potion"
    handler.add_item(item2, quantity=2)

    totals = handler.get_all_item_quantities()
    assert totals["test_item"] == 5
    assert totals["potion"] == 2
