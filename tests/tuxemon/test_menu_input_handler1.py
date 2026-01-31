# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import Mock

import pytest

from tuxemon.menu.input_handler import MenuInputHandler
from tuxemon.platform.const import buttons, intentions


def make_event(button, pressed=True, value=None):
    event = Mock()
    event.button = button
    event.pressed = pressed
    event.value = value
    return event


def fake_menu_items(items):
    menu_items = Mock()

    menu_items_list = items

    menu_items.__iter__ = lambda self=menu_items: iter(menu_items_list)
    menu_items.__getitem__ = lambda self, i: menu_items_list[i]
    menu_items.__len__ = lambda self: len(menu_items_list)

    menu_items.rect = Mock()
    menu_items.rect.left = 0
    menu_items.rect.top = 0
    menu_items.rect.collidepoint.return_value = False

    menu_items.update_rect_from_parent = Mock()

    return menu_items


@pytest.fixture
def menu():
    menu = Mock()
    menu.state_controller.is_enabled.return_value = True
    menu.escape_key_exits = True
    menu.touch_aware = True

    item1 = Mock(enabled=True)
    item1.rect.collidepoint.return_value = False

    item2 = Mock(enabled=True)
    item2.rect.collidepoint.return_value = False

    menu.menu_items = fake_menu_items([item1, item2])
    menu.selected_index = 0
    menu.get_selected_item.return_value = item1

    return menu


@pytest.fixture
def handler(menu):
    return MenuInputHandler(menu)


@pytest.mark.parametrize(
    "button",
    [
        buttons.B,
        buttons.BACK,
        intentions.MENU_CANCEL,
    ],
)
def test_escape_buttons_always_consume(handler, menu, button):
    event = make_event(button)
    assert handler.handle_event(event) is None


@pytest.mark.parametrize(
    "button",
    [
        buttons.A,
        intentions.SELECT,
    ],
)
def test_confirm_buttons_always_consume(handler, menu, button):
    event = make_event(button)
    assert handler.handle_event(event) is None


@pytest.mark.parametrize(
    "button",
    [
        buttons.UP,
        buttons.DOWN,
        buttons.LEFT,
        buttons.RIGHT,
    ],
)
def test_cursor_buttons_always_consume(handler, menu, button):
    event = make_event(button)
    assert handler.handle_event(event) is None


def test_unhandled_button_propagates(handler, menu):
    FAKE_BUTTON = object()
    event = make_event(FAKE_BUTTON)
    assert handler.handle_event(event) is event


def test_no_enabled_items_prevents_confirm(handler, menu):
    for item in menu.menu_items:
        item.enabled = False

    event = make_event(buttons.A, pressed=True)
    result = handler.handle_event(event)

    assert result is None
    menu.on_menu_selection.assert_not_called()


def test_empty_menu_prevents_interaction(handler, menu):
    menu.menu_items = fake_menu_items([])

    event = make_event(buttons.A, pressed=True)
    result = handler.handle_event(event)

    assert result is None
    menu.on_menu_selection.assert_not_called()


def test_disabled_menu_prevents_interaction(handler, menu):
    menu.state_controller.is_enabled.return_value = False

    event = make_event(buttons.A, pressed=True)
    result = handler.handle_event(event)

    assert result is None
    menu.on_menu_selection.assert_not_called()


def test_mouse_propagates_when_touch_aware_off(handler, menu):
    menu.touch_aware = False
    event = make_event(buttons.MOUSELEFT, value=(10, 10))
    assert handler.handle_event(event) is event


def test_mouse_click_outside_rect_propagates(handler, menu):
    menu.menu_items.rect.collidepoint.return_value = False
    event = make_event(buttons.MOUSELEFT, value=(999, 999))
    assert handler.handle_event(event) is event


def test_mouse_click_on_enabled_item_selects(handler, menu):
    menu.menu_items.rect.collidepoint.return_value = True
    menu.menu_items[1].rect.collidepoint.return_value = True

    event = make_event(buttons.MOUSELEFT, value=(5, 5))
    result = handler.handle_event(event)

    assert result is None
    menu.change_selection.assert_called_once_with(1)
    menu.on_menu_selection.assert_called_once()


def test_mouse_click_hits_no_item_propagates(handler, menu):
    menu.menu_items.rect.collidepoint.return_value = True
    for item in menu.menu_items:
        item.rect.collidepoint.return_value = False

    event = make_event(buttons.MOUSELEFT, value=(5, 5))
    assert handler.handle_event(event) is event


def test_mouse_invalid_position_raises(handler, menu):
    event = make_event(buttons.MOUSELEFT, value="invalid")
    with pytest.raises(ValueError):
        handler.handle_event(event)
