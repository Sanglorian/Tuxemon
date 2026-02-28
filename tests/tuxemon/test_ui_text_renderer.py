# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pygame
import pytest
from pygame.surface import Surface

from tuxemon.scaling import DefaultScaling
from tuxemon.ui.text_renderer import TextRenderer


@pytest.fixture(scope="session", autouse=True)
def pygame_init():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def renderer():
    return TextRenderer(DefaultScaling(1), (255, 255, 255))


def test_init(renderer):
    assert renderer.font_color == (255, 255, 255)


def test_shadow_text(renderer):
    surface = renderer.shadow_text("Hello, World!")
    assert isinstance(surface, Surface)


def test_shadow_text_default_colors(renderer):
    surface = renderer.shadow_text("Hello, World!")
    w, h = surface.get_size()
    assert w > 0
    assert h > 0


def test_shadow_text_custom_colors(renderer):
    surface = renderer.shadow_text(
        "Hello, World!", fg=(0, 0, 255), bg=(255, 0, 0)
    )
    w, h = surface.get_size()
    assert w > 0
    assert h > 0


def test_shadow_text_offset(renderer):
    surface = renderer.shadow_text("Hello, World!", offset=(1, 1))
    w, h = surface.get_size()
    assert w > 0
    assert h > 0


def test_shadow_text_invalid_offset(renderer):
    with pytest.raises(TypeError):
        renderer.shadow_text("Hello, World!", offset="invalid")


def test_shadow_text_invalid_fg_color(renderer):
    with pytest.raises(ValueError):
        renderer.shadow_text("Hello, World!", fg="invalid")


def test_shadow_text_invalid_bg_color(renderer):
    with pytest.raises(ValueError):
        renderer.shadow_text("Hello, World!", bg="invalid")


def test_shadow_text_surface_size(renderer):
    surface = renderer.shadow_text("Hello, World!")
    assert surface.get_width() > 0
    assert surface.get_height() > 0


def test_shadow_text_surface_alpha(renderer):
    surface = renderer.shadow_text("Hello, World!")
    assert surface.get_flags() & pygame.SRCALPHA == pygame.SRCALPHA
    assert surface.get_alpha() == 255
