# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.db import ElementModel, db
from tuxemon.element import ElementTypesHandler


class TestElementTypesHandler(unittest.TestCase):
    _fire = ElementModel(
        slug="fire", icon="gfx/ui/icons/element/fire_type.png", types=[]
    )
    _metal = ElementModel(
        slug="metal", icon="gfx/ui/icons/element/metal_type.png", types=[]
    )

    def setUp(self):
        db.database["element"] = {"fire": self._fire, "metal": self._metal}
        self.basic = ElementTypesHandler()
        self.element1 = "metal"
        self.element2 = "fire"
        self.elements = ["metal", "fire"]
        self.handler = ElementTypesHandler(self.elements)

    def test_init_with_no_types(self):
        self.assertEqual(self.basic.current, [])
        self.assertEqual(self.basic.default, [])

    def test_init_with_types(self):
        self.assertEqual(len(self.handler.current), 2)
        self.assertEqual(len(self.handler.default), 2)

    def test_set_types(self):
        self.basic.set_types(self.elements)
        self.assertEqual(len(self.basic.current), 2)

    def test_reset_to_default(self):
        new_element = "metal"
        self.handler.set_types([new_element])
        self.handler.reset_to_default()
        self.assertEqual(len(self.handler.current), 2)

    def test_get_type_slugs(self):
        self.assertEqual(self.handler.get_type_slugs(), self.elements)

    def test_has_type(self):
        self.assertTrue(self.handler.has_type(self.element1))
        self.assertFalse(self.handler.has_type("non_existent_type"))

    def test_primary_type(self):
        self.assertEqual(self.handler.primary.slug, self.element1)
        self.assertIsNotNone(self.handler.primary)
