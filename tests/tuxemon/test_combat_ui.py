# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock

from tuxemon.ui.combat_bars import CombatBars


class TestCombatBars(unittest.TestCase):

    def setUp(self):
        self.graphics = MagicMock()
        self.combat_ui = CombatBars(self.graphics)

    def test_init(self):
        self.assertEqual(self.combat_ui._hp_bars, {})
        self.assertEqual(self.combat_ui._exp_bars, {})

    def test_draw_hp_bars(self):
        self.graphics.hud.hp_bar_player = True
        self.graphics.hud.hp_bar_opponent = True
        hud = {
            MagicMock(player=True): MagicMock(image=MagicMock()),
            MagicMock(player=False): MagicMock(image=MagicMock()),
        }
        self.combat_ui._hp_bars = {
            monster: MagicMock() for monster in hud.keys()
        }
        self.combat_ui.create_rect_for_bar = MagicMock(
            return_value=MagicMock()
        )
        self.combat_ui.draw_hp_bars(hud)
        for monster, sprite in hud.items():
            if sprite.player:
                self.combat_ui._hp_bars[monster].draw.assert_called_once_with(
                    sprite.image,
                    self.combat_ui.create_rect_for_bar.return_value,
                )
            else:
                self.combat_ui._hp_bars[monster].draw.assert_called_once_with(
                    sprite.image,
                    self.combat_ui.create_rect_for_bar.return_value,
                )

    def test_draw_hp_bars_no_player(self):
        self.graphics.hud.hp_bar_player = False
        self.graphics.hud.hp_bar_opponent = True
        hud = {
            MagicMock(player=True): MagicMock(image=MagicMock()),
            MagicMock(player=False): MagicMock(image=MagicMock()),
        }
        self.combat_ui._hp_bars = {
            monster: MagicMock() for monster in hud.keys()
        }
        self.combat_ui.create_rect_for_bar = MagicMock(
            return_value=MagicMock()
        )
        self.combat_ui.draw_hp_bars(hud)
        for monster, sprite in hud.items():
            if sprite.player:
                self.assertFalse(self.combat_ui._hp_bars[monster].draw.called)
            else:
                self.combat_ui._hp_bars[monster].draw.assert_called_once_with(
                    sprite.image,
                    self.combat_ui.create_rect_for_bar.return_value,
                )

    def test_draw_exp_bars(self):
        self.graphics.hud.exp_bar_player = True
        hud = {
            MagicMock(player=True): MagicMock(image=MagicMock()),
            MagicMock(player=False): MagicMock(image=MagicMock()),
        }
        self.combat_ui._exp_bars = {
            monster: MagicMock() for monster in hud.keys()
        }
        self.combat_ui.create_rect_for_bar = MagicMock(
            return_value=MagicMock()
        )
        self.combat_ui.draw_exp_bars(hud)
        for monster, sprite in hud.items():
            if sprite.player:
                self.combat_ui._exp_bars[monster].draw.assert_called_once_with(
                    sprite.image,
                    self.combat_ui.create_rect_for_bar.return_value,
                )
            else:
                self.assertFalse(self.combat_ui._exp_bars[monster].draw.called)

    def test_create_rect_for_bar(self):
        hud = MagicMock()
        hud.image.get_width.return_value = 100
        rect = self.combat_ui.create_rect_for_bar(hud, 70, 8, 0)
        self.assertEqual(rect.width, 350)
        self.assertEqual(rect.height, 40)
        self.assertEqual(rect.right, 60)
        self.assertEqual(rect.top, 0)

    def test_draw_all_ui(self):
        hud = {
            MagicMock(player=True): MagicMock(image=MagicMock()),
            MagicMock(player=False): MagicMock(image=MagicMock()),
        }
        self.combat_ui.draw_hp_bars = MagicMock()
        self.combat_ui.draw_exp_bars = MagicMock()
        self.combat_ui.draw_bars(hud)
        self.combat_ui.draw_hp_bars.assert_called_once_with(hud)
        self.combat_ui.draw_exp_bars.assert_called_once_with(hud)
