# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pygame
import pytest

from tuxemon.menu.cursor import MenuCursorController
from tuxemon.sprite import SpriteGroup


@pytest.fixture(scope="module", autouse=True)
def pygame_env():
    pygame.init()
    pygame.display.set_mode((0, 0))
    yield
    pygame.quit()


@pytest.fixture
def menu_sprites():
    return SpriteGroup()


@pytest.fixture
def fake_context():
    ctx = MagicMock()
    ctx.scaling = MagicMock()
    ctx.scaling.scale_int = lambda x: x * 2
    ctx.scaling.scale_tuple = lambda t: tuple(x * 2 for x in t)
    return ctx


@pytest.fixture
def controller(menu_sprites, fake_context):
    cursor_filename = "gfx/arrow.png"
    get_selected_item = MagicMock(return_value=None)
    animate = MagicMock(return_value=None)
    duration = 1.0
    remove_animations = MagicMock()
    ctrl = MenuCursorController(
        cursor_filename,
        menu_sprites,
        get_selected_item,
        animate,
        duration,
        fake_context,
        remove_animations,
    )
    return ctrl


def test_init(controller, menu_sprites):
    assert controller.arrow is not None
    assert controller.sprites is menu_sprites
    assert controller.get_item is controller.get_item
    assert controller.animate is controller.animate
    assert controller.duration == 1.0
    assert controller.remove_animations is controller.remove_animations


def test_get_margin(controller):
    margin = controller.get_margin()
    assert isinstance(margin, tuple)
    assert len(margin) == 2


def test_show_cursor(controller):
    controller.hide_cursor()
    controller.show_cursor()
    assert controller.arrow in controller.sprites


def test_hide_cursor(controller):
    controller.show_cursor()
    controller.hide_cursor()
    assert controller.arrow not in controller.sprites


@pytest.mark.parametrize("animate_flag", [True, False])
def test_trigger_cursor_update(controller, animate_flag):
    item = MagicMock()
    item.rect.midleft = (10, 20)
    controller.get_item.return_value = item
    animation = controller.trigger_cursor_update(animate=animate_flag)
    assert animation is None

    if animate_flag:
        controller.animate.assert_called_once()
        controller.remove_animations.assert_called_once_with(
            controller.arrow.rect
        )
    else:
        controller.animate.assert_not_called()


def test_trigger_cursor_update_no_item(controller):
    controller.get_item.return_value = None
    animation = controller.trigger_cursor_update(animate=True)
    assert animation is None


def test_update_selection_focus(controller):
    previous_item = MagicMock()
    new_item = MagicMock()
    controller.update_selection_focus(previous_item, new_item)
    assert previous_item.in_focus is False
    assert new_item.in_focus is True
    previous_item.update_image.assert_called_once()
    new_item.update_image.assert_called_once()


def test_update_selection_focus_no_previous_item(controller):
    new_item = MagicMock()
    controller.update_selection_focus(None, new_item)
    assert new_item.in_focus is True
    new_item.update_image.assert_called_once()


def test_update_selection_focus_no_new_item(controller):
    previous_item = MagicMock()
    controller.update_selection_focus(previous_item, None)
    assert previous_item.in_focus is False
    previous_item.update_image.assert_called_once()


def test_update_focus(controller):
    item = MagicMock()
    controller._update_focus(item, True)
    assert item.in_focus is True
    item.update_image.assert_called_once()


def test_ensure_cursor_visible(controller):
    controller._ensure_cursor_visible(True)
    assert controller.arrow in controller.sprites
    controller._ensure_cursor_visible(False)
    assert controller.arrow not in controller.sprites


def test_ensure_cursor_visible_already_visible(controller):
    controller.show_cursor()
    controller._ensure_cursor_visible(True)
    assert controller.arrow in controller.sprites


def test_ensure_cursor_visible_already_hidden(controller):
    controller.hide_cursor()
    controller._ensure_cursor_visible(False)
    assert controller.arrow not in controller.sprites
