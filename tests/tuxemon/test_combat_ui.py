# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock

from tuxemon.tools import scale
from tuxemon.ui.combat_bars import CombatBars


class TestCombatBars(unittest.TestCase):

    def setUp(self):
        self.combat_ui = CombatBars()
        self.graphics = MagicMock()
        self.graphics.hud.hp_bar_player = True
        self.graphics.hud.hp_bar_opponent = True
        self.graphics.hud.exp_bar_player = True
        self.graphics.hud.hp_bar_width = 70
        self.graphics.hud.hp_bar_height = 8
        self.graphics.hud.hp_player_top = 18
        self.graphics.hud.hp_opponent_top = 12
        self.graphics.hud.exp_bar_height = 6
        self.graphics.hud.exp_bar_top = 31
        self.graphics.hud.bar_right_padding = 8

    def test_init(self):
        self.assertEqual(self.combat_ui._hp_bars, {})
        self.assertEqual(self.combat_ui._exp_bars, {})

    def test_draw_bars_hp_and_exp(self):
        monster_player = MagicMock()
        monster_player.hp_ratio = 0.75
        monster_player.experience_progress_percent = 0.5

        monster_opponent = MagicMock()
        monster_opponent.hp_ratio = 0.5
        monster_opponent.experience_progress_percent = 0.0

        hud = {
            monster_player: MagicMock(player=True, image=MagicMock()),
            monster_opponent: MagicMock(player=False, image=MagicMock()),
        }

        self.combat_ui._hp_bars = {
            monster: MagicMock() for monster in hud.keys()
        }
        self.combat_ui._exp_bars = {
            monster: MagicMock() for monster in hud.keys()
        }

        self.combat_ui.create_rect_for_bar = MagicMock(
            return_value=MagicMock()
        )

        self.combat_ui.draw_bars(hud, self.graphics)

        for monster, sprite in hud.items():
            if sprite.player:
                self.combat_ui._hp_bars[monster].draw.assert_called_once_with(
                    sprite.image,
                    self.combat_ui.create_rect_for_bar.return_value,
                )
                self.combat_ui._exp_bars[monster].draw.assert_called_once_with(
                    sprite.image,
                    self.combat_ui.create_rect_for_bar.return_value,
                )
            else:
                self.combat_ui._hp_bars[monster].draw.assert_called_once_with(
                    sprite.image,
                    self.combat_ui.create_rect_for_bar.return_value,
                )
                self.assertFalse(self.combat_ui._exp_bars[monster].draw.called)

    def test_create_rect_for_bar(self):
        hud = MagicMock()
        hud.image.get_width.return_value = 100
        rect = self.combat_ui.create_rect_for_bar(hud, 70, 8, 0, 8)
        self.assertEqual(rect.width, scale(70))
        self.assertEqual(rect.height, scale(8))
        self.assertEqual(rect.right, hud.image.get_width() - scale(8))
        self.assertEqual(rect.top, scale(0))

    def test_get_hp_bar_initializes_with_monster_value(self):
        monster = MagicMock()
        monster.hp_ratio = 0.6
        bar = self.combat_ui.get_hp_bar(monster)
        self.assertEqual(bar.value, 0.6)

    def test_get_exp_bar_initializes_with_monster_value(self):
        monster = MagicMock()
        monster.experience_progress_percent = 0.4
        bar = self.combat_ui.get_exp_bar(monster)
        self.assertEqual(bar.value, 0.4)

    def test_remove_monster_clears_bars(self):
        monster = MagicMock()
        monster.hp_ratio = 0.5
        monster.experience_progress_percent = 0.3
        self.combat_ui.get_hp_bar(monster)
        self.combat_ui.get_exp_bar(monster)
        self.assertIn(monster, self.combat_ui._hp_bars)
        self.assertIn(monster, self.combat_ui._exp_bars)

        self.combat_ui.remove_monster(monster)
        self.assertNotIn(monster, self.combat_ui._hp_bars)
        self.assertNotIn(monster, self.combat_ui._exp_bars)

    def test_clear_all_removes_all_bars(self):
        m1, m2 = MagicMock(), MagicMock()
        m1.hp_ratio, m1.experience_progress_percent = 0.5, 0.2
        m2.hp_ratio, m2.experience_progress_percent = 0.8, 0.7
        self.combat_ui.get_hp_bar(m1)
        self.combat_ui.get_exp_bar(m1)
        self.combat_ui.get_hp_bar(m2)
        self.combat_ui.get_exp_bar(m2)
        self.assertTrue(self.combat_ui._hp_bars)
        self.assertTrue(self.combat_ui._exp_bars)

        self.combat_ui.clear_all()
        self.assertEqual(self.combat_ui._hp_bars, {})
        self.assertEqual(self.combat_ui._exp_bars, {})
