# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock

from tuxemon.npc import NPC
from tuxemon.ui.combat_layout import LayoutManager, prepare_layout


class TestLayoutManager(unittest.TestCase):

    def test_init(self):
        scaled_layouts = {
            "RIGHT_COMBAT": {"key": (1, 2, 3, 4)},
            "LEFT_COMBAT": {"key": (5, 6, 7, 8)},
        }
        layout_groups = {
            1: ["RIGHT_COMBAT"],
            2: ["RIGHT_COMBAT", "LEFT_COMBAT"],
        }

        layout_manager = LayoutManager(scaled_layouts, layout_groups)

        self.assertIn(1, layout_manager._layouts_by_player_count)
        self.assertIn(2, layout_manager._layouts_by_player_count)

    def test_get_raw_layout_for_player_valid(self):
        scaled_layouts = {
            "RIGHT_COMBAT": {"key": (1, 2, 3, 4)},
            "LEFT_COMBAT": {"key": (5, 6, 7, 8)},
        }
        layout_groups = {
            1: ["RIGHT_COMBAT"],
            2: ["RIGHT_COMBAT", "LEFT_COMBAT"],
        }
        layout_manager = LayoutManager(scaled_layouts, layout_groups)

        raw_layout = layout_manager.get_raw_layout_for_player(0, 2)

        self.assertEqual(raw_layout, {"key": (1, 2, 3, 4)})

    def test_get_raw_layout_for_player_invalid_player_count(self):
        scaled_layouts = {
            "RIGHT_COMBAT": {"key": (1, 2, 3, 4)},
            "LEFT_COMBAT": {"key": (5, 6, 7, 8)},
        }
        layout_groups = {
            1: ["RIGHT_COMBAT"],
            2: ["RIGHT_COMBAT", "LEFT_COMBAT"],
        }
        layout_manager = LayoutManager(scaled_layouts, layout_groups)

        with self.assertRaises(ValueError):
            layout_manager.get_raw_layout_for_player(0, 3)

    def test_get_raw_layout_for_player_invalid_player_index(self):
        scaled_layouts = {
            "RIGHT_COMBAT": {"key": (1, 2, 3, 4)},
            "LEFT_COMBAT": {"key": (5, 6, 7, 8)},
        }
        layout_groups = {
            1: ["RIGHT_COMBAT"],
            2: ["RIGHT_COMBAT", "LEFT_COMBAT"],
        }
        layout_manager = LayoutManager(scaled_layouts, layout_groups)

        with self.assertRaises(IndexError):
            layout_manager.get_raw_layout_for_player(2, 2)

    def test_prepare_all_player_layouts(self):
        scaled_layouts = {
            "RIGHT_COMBAT": {"key": (1, 2, 3, 4)},
            "LEFT_COMBAT": {"key": (5, 6, 7, 8)},
        }
        layout_groups = {
            1: ["RIGHT_COMBAT"],
            2: ["RIGHT_COMBAT", "LEFT_COMBAT"],
        }
        layout_manager = LayoutManager(scaled_layouts, layout_groups)
        players = [MagicMock(spec=NPC) for _ in range(2)]

        layouts = layout_manager.prepare_all_player_layouts(players)

        self.assertEqual(len(layouts), 2)
        for player, layout in layouts.items():
            self.assertIsInstance(player, MagicMock)
            self.assertIsInstance(layout, dict)

    def test_prepare_layout(self):
        scaled_layouts = {
            "RIGHT_COMBAT": {"key": (1, 2, 3, 4)},
            "LEFT_COMBAT": {"key": (5, 6, 7, 8)},
        }
        layout_groups = {
            1: ["RIGHT_COMBAT"],
            2: ["RIGHT_COMBAT", "LEFT_COMBAT"],
        }
        layout_manager = LayoutManager(scaled_layouts, layout_groups)
        players = [MagicMock(spec=NPC) for _ in range(2)]

        layouts = prepare_layout(players, layout_manager)

        self.assertEqual(len(layouts), 2)
        for player, layout in layouts.items():
            self.assertIsInstance(player, MagicMock)
            self.assertIsInstance(layout, dict)

    def test_prepare_all_player_layouts_empty_player_list(self):
        scaled_layouts = {
            "RIGHT_COMBAT": {"key": (1, 2, 3, 4)},
            "LEFT_COMBAT": {"key": (5, 6, 7, 8)},
        }
        layout_groups = {
            1: ["RIGHT_COMBAT"],
            2: ["RIGHT_COMBAT", "LEFT_COMBAT"],
        }
        layout_manager = LayoutManager(scaled_layouts, layout_groups)
        players = []

        layouts = layout_manager.prepare_all_player_layouts(players)

        self.assertEqual(layouts, {})

    def test_prepare_all_player_layouts_single_player(self):
        scaled_layouts = {
            "RIGHT_COMBAT": {"key": (1, 2, 3, 4)},
            "LEFT_COMBAT": {"key": (5, 6, 7, 8)},
        }
        layout_groups = {
            1: ["RIGHT_COMBAT"],
            2: ["RIGHT_COMBAT", "LEFT_COMBAT"],
        }
        layout_manager = LayoutManager(scaled_layouts, layout_groups)
        players = [MagicMock(spec=NPC)]

        layouts = layout_manager.prepare_all_player_layouts(players)

        self.assertEqual(len(layouts), 1)

    def test_get_raw_layout_for_player_zero_players(self):
        scaled_layouts = {
            "RIGHT_COMBAT": {"key": (1, 2, 3, 4)},
            "LEFT_COMBAT": {"key": (5, 6, 7, 8)},
        }
        layout_groups = {
            1: ["RIGHT_COMBAT"],
            2: ["RIGHT_COMBAT", "LEFT_COMBAT"],
        }
        layout_manager = LayoutManager(scaled_layouts, layout_groups)

        with self.assertRaises(ValueError):
            layout_manager.get_raw_layout_for_player(0, 0)

    def test_get_raw_layout_for_player_negative_player_index(self):
        scaled_layouts = {
            "RIGHT_COMBAT": {"key": (1, 2, 3, 4)},
            "LEFT_COMBAT": {"key": (5, 6, 7, 8)},
        }
        layout_groups = {
            1: ["RIGHT_COMBAT"],
            2: ["RIGHT_COMBAT", "LEFT_COMBAT"],
        }
        layout_manager = LayoutManager(scaled_layouts, layout_groups)

        with self.assertRaises(IndexError):
            layout_manager.get_raw_layout_for_player(-1, 2)

    def test_get_raw_layout_for_player_negative_total_players(self):
        scaled_layouts = {
            "RIGHT_COMBAT": {"key": (1, 2, 3, 4)},
            "LEFT_COMBAT": {"key": (5, 6, 7, 8)},
        }
        layout_groups = {
            1: ["RIGHT_COMBAT"],
            2: ["RIGHT_COMBAT", "LEFT_COMBAT"],
        }
        layout_manager = LayoutManager(scaled_layouts, layout_groups)

        with self.assertRaises(ValueError):
            layout_manager.get_raw_layout_for_player(0, -1)
