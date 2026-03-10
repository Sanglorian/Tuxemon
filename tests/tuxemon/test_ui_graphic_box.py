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


@pytest.fixture
def border_img():
    img = Surface((30, 30))
    img.fill((255, 255, 255))
    return img


@pytest.fixture
def default_rect():
    return Rect(0, 0, 100, 100)


def test_graphicbox_init_defaults(default_rect, border_img):
    box = GraphicBox(default_rect, border_img)
    assert box._background is None
    assert box._color is None
    assert box._fill_tiles is False
    assert len(box._tiles) == 9
    assert box._tile_size == (10, 10)


def test_graphicbox_set_border_valid(default_rect, border_img):
    img = Surface((12, 12))  # divisible by 3
    box = GraphicBox(default_rect, border_img)
    box._set_border(img)
    assert box._tile_size == (4, 4)
    assert len(box._tiles) == 9


def test_graphicbox_set_border_invalid_size(default_rect, border_img):
    img = Surface((10, 12))  # not divisible by 3
    box = GraphicBox(default_rect, border_img)
    with pytest.raises(ValueError):
        box._set_border(img)


def test_graphicbox_rejects_non_3x3_border(default_rect):
    img = Surface((40, 40))  # 40 % 3 != 0
    box = GraphicBox(default_rect, img)
    assert box._tiles == {}
    assert box._tile_size == (0, 0)


def test_graphicbox_border_tile_size(default_rect):
    img = Surface((30, 30))
    box = GraphicBox(default_rect, img)
    assert box._tile_size == (10, 10)


def test_graphicbox_calc_inner_rect_no_tiles(default_rect, border_img):
    rect = Rect(0, 0, 100, 100)
    box = GraphicBox(default_rect, border_img)
    box._tiles = {}  # force no tiles
    box._tile_size = (0, 0)  # force no tile size
    assert box.calc_inner_rect(rect) == rect


def test_graphicbox_calc_inner_rect_with_tiles(default_rect, border_img):
    box = GraphicBox(default_rect, border_img)
    box._tiles = {"c": Surface((10, 10))}
    box._tile_size = (10, 10)

    rect = Rect(0, 0, 100, 100)
    inner = box.calc_inner_rect(rect)
    assert inner == Rect(10, 10, 80, 80)


def test_graphicbox_draw_no_background_or_color(
    default_rect, border_img, surface
):
    box = GraphicBox(default_rect, border_img)
    rect = Rect(0, 0, 100, 100)
    box._draw(surface, rect)  # should not crash


def test_graphicbox_draw_with_background(default_rect, border_img, surface):
    box = GraphicBox(default_rect, border_img)
    box._background = Surface((100, 100))
    rect = Rect(0, 0, 100, 100)
    box._draw(surface, rect)


def test_graphicbox_draw_with_color(default_rect, border_img, surface):
    box = GraphicBox(default_rect, border_img)
    box._color = (255, 0, 0)
    rect = Rect(0, 0, 100, 100)
    box._draw(surface, rect)


def test_graphicbox_update_image(default_rect, border_img):
    box = GraphicBox(default_rect, border_img)
    box._rect = Rect(0, 0, 100, 100)
    box.update_image()
    assert box.image is not None


def test_tiles_are_independent_copies(default_rect):
    img = Surface((30, 30))
    img.fill((10, 10, 10))
    box = GraphicBox(default_rect, img)

    # Mutate original
    img.fill((200, 0, 0))

    # Tiles should NOT change
    assert box._tiles["c"].get_at((0, 0)) == (10, 10, 10, 255)


def test_border_clipping_no_crash_and_no_overlap(default_rect, surface):
    img = Surface((30, 30))
    img.fill((255, 255, 255))
    box = GraphicBox(default_rect, img)
    rect = Rect(0, 0, 37, 37)  # not divisible by tile size
    box._draw(surface, rect)  # should not crash


def test_corner_tiles_positions(default_rect):
    img = Surface((30, 30))
    box = GraphicBox(default_rect, img)
    rect = Rect(0, 0, 30, 30)

    # Draw into a fresh surface
    surf = Surface(rect.size)
    box._draw(surf, rect)

    # Corners must be drawn exactly at these coords
    assert surf.get_at((0, 0)) is not None
    assert surf.get_at((29, 0)) is not None
    assert surf.get_at((0, 29)) is not None
    assert surf.get_at((29, 29)) is not None


def test_update_image_requires_rect(border_img):
    with pytest.raises(ValueError):
        GraphicBox(Rect(0, 0, 0, 0), border_img)
