# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.tools import scale
from tuxemon.ui.combat_bars import CombatBars


@pytest.fixture
def combat_ui():
    return CombatBars()


@pytest.fixture
def graphics():
    g = MagicMock()
    g.hud.hp_bar_player = True
    g.hud.hp_bar_opponent = True
    g.hud.exp_bar_player = True
    g.hud.hp_bar_width = 70
    g.hud.hp_bar_height = 8
    g.hud.hp_player_top = 18
    g.hud.hp_opponent_top = 12
    g.hud.exp_bar_height = 6
    g.hud.exp_bar_top = 31
    g.hud.bar_right_padding = 8
    return g


def test_init(combat_ui):
    assert combat_ui._hp_bars == {}
    assert combat_ui._exp_bars == {}


@pytest.mark.parametrize(
    "hp_ratio, exp_ratio",
    [
        (0.75, 0.5),  # player
        (0.5, 0.0),  # opponent
    ],
)
def test_draw_bars_hp_and_exp(combat_ui, graphics, hp_ratio, exp_ratio):
    monster = MagicMock()
    monster.hp_ratio = hp_ratio
    monster.experience_progress_percent = exp_ratio

    is_player = exp_ratio > 0

    hud = {monster: MagicMock(player=is_player, image=MagicMock())}

    combat_ui._hp_bars = {monster: MagicMock()}
    combat_ui._exp_bars = {monster: MagicMock()}
    combat_ui.create_rect_for_bar = MagicMock(return_value=MagicMock())
    combat_ui.draw_bars(hud, graphics)
    combat_ui._hp_bars[monster].draw.assert_called_once()

    if is_player:
        combat_ui._exp_bars[monster].draw.assert_called_once()
    else:
        assert not combat_ui._exp_bars[monster].draw.called


def test_create_rect_for_bar(combat_ui):
    hud = MagicMock()
    hud.image.get_width.return_value = 100
    rect = combat_ui.create_rect_for_bar(hud, 70, 8, 0, 8)
    assert rect.width == scale(70)
    assert rect.height == scale(8)
    assert rect.right == 100 - scale(8)
    assert rect.top == scale(0)


@pytest.mark.parametrize("ratio", [0.0, 0.4, 0.6, 1.0])
def test_get_hp_bar_initializes_with_monster_value(combat_ui, ratio):
    monster = MagicMock()
    monster.hp_ratio = ratio
    bar = combat_ui.get_hp_bar(monster)
    assert bar.value == ratio


@pytest.mark.parametrize("ratio", [0.0, 0.2, 0.4, 0.9])
def test_get_exp_bar_initializes_with_monster_value(combat_ui, ratio):
    monster = MagicMock()
    monster.experience_progress_percent = ratio
    bar = combat_ui.get_exp_bar(monster)
    assert bar.value == ratio


def test_remove_monster_clears_bars(combat_ui):
    monster = MagicMock()
    monster.hp_ratio = 0.5
    monster.experience_progress_percent = 0.3
    combat_ui.get_hp_bar(monster)
    combat_ui.get_exp_bar(monster)
    assert monster in combat_ui._hp_bars
    assert monster in combat_ui._exp_bars
    combat_ui.remove_monster(monster)
    assert monster not in combat_ui._hp_bars
    assert monster not in combat_ui._exp_bars


def test_clear_all_removes_all_bars(combat_ui):
    m1, m2 = MagicMock(), MagicMock()
    m1.hp_ratio, m1.experience_progress_percent = 0.5, 0.2
    m2.hp_ratio, m2.experience_progress_percent = 0.8, 0.7
    combat_ui.get_hp_bar(m1)
    combat_ui.get_exp_bar(m1)
    combat_ui.get_hp_bar(m2)
    combat_ui.get_exp_bar(m2)
    assert combat_ui._hp_bars
    assert combat_ui._exp_bars
    combat_ui.clear_all()
    assert combat_ui._hp_bars == {}
    assert combat_ui._exp_bars == {}
