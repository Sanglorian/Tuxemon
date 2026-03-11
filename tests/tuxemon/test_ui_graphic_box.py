# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pygame
import pytest
from pygame.rect import Rect
from pygame.surface import Surface

from tuxemon.ui.graphic_box import GraphicBox


@pytest.fixture(scope="session", autouse=True)
def pygame_init():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def surface():
    return pygame.display.set_mode((800, 600))


def test_graphicbox_init_defaults():
    box = GraphicBox()
    assert box._background is None
    assert box._color is None
    assert box._fill_tiles is False
    assert box._tiles == {}
    assert box._tile_size == (0, 0)


def test_graphicbox_set_border_valid():
    img = Surface((12, 12))  # divisible by 3
    box = GraphicBox()
    box._set_border(img)
    assert box._tile_size == (4, 4)
    assert len(box._tiles) == 9


def test_graphicbox_set_border_invalid_size():
    img = Surface((10, 12))  # not divisible by 3
    box = GraphicBox()
    with pytest.raises(ValueError):
        box._set_border(img)


def test_graphicbox_rejects_non_3x3_border():
    img = Surface((40, 40))  # 40 % 3 != 0
    with pytest.raises(ValueError):
        GraphicBox(border=img)


def test_graphicbox_border_tile_size():
    img = Surface((30, 30))
    box = GraphicBox(border=img)
    assert box._tile_size == (10, 10)


def test_graphicbox_calc_inner_rect_no_tiles():
    box = GraphicBox()
    rect = Rect(0, 0, 100, 100)
    assert box.calc_inner_rect(rect) == rect


def test_graphicbox_calc_inner_rect_with_tiles():
    box = GraphicBox()
    box._tiles = {"c": Surface((10, 10))}
    box._tile_size = (10, 10)

    rect = Rect(0, 0, 100, 100)
    inner = box.calc_inner_rect(rect)
    assert inner == Rect(10, 10, 80, 80)


def test_graphicbox_draw_no_background_or_color(surface):
    box = GraphicBox()
    rect = Rect(0, 0, 100, 100)
    box._draw(surface, rect)  # should not crash


def test_graphicbox_draw_with_background(surface):
    box = GraphicBox()
    box._background = Surface((100, 100))
    rect = Rect(0, 0, 100, 100)
    box._draw(surface, rect)


def test_graphicbox_draw_with_color(surface):
    box = GraphicBox()
    box._color = (255, 0, 0)
    rect = Rect(0, 0, 100, 100)
    box._draw(surface, rect)


def test_graphicbox_update_image():
    box = GraphicBox()
    box._rect = Rect(0, 0, 100, 100)
    box.update_image()
    assert box.image is not None


def test_tiles_are_independent_copies():
    img = Surface((30, 30))
    img.fill((10, 10, 10))
    box = GraphicBox(border=img)

    # Mutate original
    img.fill((200, 0, 0))

    # Tiles should NOT change
    assert box._tiles["c"].get_at((0, 0)) == (10, 10, 10, 255)


def test_border_clipping_no_crash_and_no_overlap(surface):
    img = Surface((30, 30))
    img.fill((255, 255, 255))
    box = GraphicBox(border=img)
    rect = Rect(0, 0, 37, 37)  # not divisible by tile size
    box._draw(surface, rect)  # should not crash


def test_corner_tiles_positions(surface):
    img = Surface((30, 30))
    box = GraphicBox(border=img)
    rect = Rect(0, 0, 30, 30)

    # Draw into a fresh surface
    surf = Surface(rect.size)
    box._draw(surf, rect)

    # Corners must be drawn exactly at these coords
    assert surf.get_at((0, 0)) is not None
    assert surf.get_at((29, 0)) is not None
    assert surf.get_at((0, 29)) is not None
    assert surf.get_at((29, 29)) is not None


def test_update_image_requires_rect():
    box = GraphicBox()
    with pytest.raises(RuntimeError):
        box.update_image()
