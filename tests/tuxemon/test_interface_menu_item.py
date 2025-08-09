# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock

from pygame import Surface

from tuxemon.menu.interface import MenuItem


class TestMenuItem(unittest.TestCase):

    def setUp(self):
        self.image = Surface((10, 10))
        self.game_object = MagicMock()

    def test_init_default(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        self.assertEqual(menu_item.label, "Test Label")
        self.assertEqual(menu_item.description, "Test Description")
        self.assertEqual(menu_item.enabled, True)

    def test_init_custom(self):
        menu_item = MenuItem(
            self.image,
            "Test Label",
            "Test Description",
            self.game_object,
            enabled=False,
            position=(100, 100),
        )
        self.assertEqual(menu_item.label, "Test Label")
        self.assertEqual(menu_item.description, "Test Description")
        self.assertEqual(menu_item.enabled, False)

    def test_update_image_focus(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        menu_item._in_focus = True
        menu_item.update_image = MagicMock()
        menu_item.update_image()

    def test_update_image_enabled(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        menu_item.enabled = False
        menu_item.update_image = MagicMock()
        menu_item.update_image()

    def test_enabled_property(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        self.assertTrue(menu_item.enabled)
        menu_item.enabled = False
        self.assertFalse(menu_item.enabled)

    def test_in_focus_property(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        self.assertFalse(menu_item.in_focus)
        menu_item.in_focus = True
        self.assertTrue(menu_item.in_focus)

    def test_repr(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        self.assertIn("Test Label", str(menu_item))
        self.assertIn("enabled=True", str(menu_item))
