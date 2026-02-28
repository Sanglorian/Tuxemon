# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pygame
import pytest

from tuxemon.scaling import DefaultScaling
from tuxemon.ui.draw import TextOverflow, iter_render_text
from tuxemon.ui.text import TextArea


class DummyChar:
    def __init__(self, ch="X"):
        self.surface = pygame.Surface((1, 1))
        self.rect = self.surface.get_rect()


def dummy_iter_render_text(**kwargs):
    for _ in kwargs["text"]:
        yield DummyChar()


@pytest.fixture(scope="session", autouse=True)
def pygame_init():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def font():
    return pygame.font.Font(None, 16)


@pytest.fixture
def text_area(font):
    ta = TextArea(
        font=font,
        font_color=(255, 255, 255),
        scaling=DefaultScaling(1),
    )
    ta._iter = None
    return ta


@pytest.fixture
def stress_text_area(font):
    ta = TextArea(
        font=font,
        font_color=(255, 255, 255),
        scaling=DefaultScaling(1),
    )
    ta.rect = pygame.Rect(0, 0, 100, 20)
    return ta


def test_initial_state(text_area):
    assert text_area.text == ""
    assert text_area.drawing_text is False


def test_text_setter_triggers_animation(text_area):
    text_area._start_text_animation = lambda: setattr(
        text_area, "drawing_text", True
    )
    text_area.text = "Hello"
    assert text_area.text == "Hello"
    assert text_area.drawing_text is True


def test_len_returns_length(text_area):
    text_area.text = "abc"
    assert len(text_area) == 3


def test_iter_and_next(text_area):
    text_area._iter = iter([DummyChar(), DummyChar()])
    text_area.animated = True
    text_area.drawing_text = True
    next(text_area)
    assert text_area.drawing_text is True
    with pytest.raises(StopIteration):
        while True:
            next(text_area)
    assert text_area.drawing_text is False


def test_non_animated_text_sets_image_directly(text_area):
    text_area.animated = False
    text_area.text = "Direct"
    assert text_area.image is not None


def test_set_background_color(text_area):
    text_area.rect = pygame.Rect(0, 0, 10, 10)
    text_area.set_background(background_color=(255, 0, 0))
    assert text_area.image.get_at((0, 0)) == pygame.Color(255, 0, 0, 255)


def test_set_background_image(text_area):
    surf = pygame.Surface((10, 10))
    surf.fill((0, 255, 0))
    text_area.rect = pygame.Rect(0, 0, 10, 10)
    text_area.set_background(background_image=surf)
    assert text_area.image.get_at((0, 0)) == pygame.Color(0, 255, 0, 255)


def test_overflow_behavior_setter(text_area):
    text_area.set_overflow_behavior(TextOverflow.WRAP)
    assert text_area.overflow_behavior == TextOverflow.WRAP


def test_start_text_animation_resets_surface(text_area):
    text_area.rect = pygame.Rect(0, 0, 10, 10)
    global iter_render_text
    old_iter = iter_render_text
    iter_render_text = dummy_iter_render_text
    try:
        text_area.text = "abc"
        assert text_area.drawing_text is True
        assert text_area._iter is not None
    finally:
        iter_render_text = old_iter


def test_next_raises_stopiteration_when_not_animated(text_area):
    text_area.animated = False
    with pytest.raises(StopIteration):
        next(text_area)


def test_text_setter_same_value_does_not_restart_animation(text_area):
    text_area.text = "abc"
    text_area.drawing_text = False
    text_area.text = "abc"
    assert text_area.drawing_text is False


def test_fast_click_before_update(stress_text_area):
    stress_text_area.text = "FastClick"
    stress_text_area.drawing_text = True
    for _ in stress_text_area:
        pass
    assert stress_text_area.drawing_text is False
    assert stress_text_area.text == "FastClick"


def test_update_progressive_render(stress_text_area):
    stress_text_area.text = "Hello"
    stress_text_area.drawing_text = True
    try:
        while True:
            next(stress_text_area)
    except StopIteration:
        pass
    assert stress_text_area.drawing_text is False


def test_empty_string(stress_text_area):
    stress_text_area.text = ""
    assert stress_text_area.drawing_text is False
    assert stress_text_area.text == ""


def test_repeated_text_changes(stress_text_area):
    for msg in ["One", "Two", "Three"]:
        stress_text_area.text = msg
        for _ in stress_text_area:
            pass
        assert stress_text_area.text == msg
        assert stress_text_area.drawing_text is False


def test_surface_size_zero(font):
    ta = TextArea(
        font=font,
        font_color=(255, 255, 255),
        scaling=DefaultScaling(1),
    )
    ta.rect = pygame.Rect(0, 0, 0, 0)
    ta.text = "ZeroRect"
    assert ta.drawing_text or ta.text == "ZeroRect"


def test_drawing_text_stays_true_until_stopiteration(stress_text_area):
    stress_text_area.text = "Hello"
    assert stress_text_area.drawing_text is True

    count = 0
    try:
        while True:
            next(stress_text_area)
            count += 1
            assert stress_text_area.drawing_text is True
    except StopIteration:
        pass

    assert count == len(stress_text_area.text)
    assert stress_text_area.drawing_text is False


def test_non_animated_text_is_fully_rendered_immediately(stress_text_area):
    stress_text_area.animated = False
    stress_text_area.text = "Static Text"
    assert stress_text_area.text == "Static Text"
    assert stress_text_area.drawing_text is False


def test_len_after_setting_empty_text(stress_text_area):
    stress_text_area.text = "A B C"
    assert len(stress_text_area) == 5
    stress_text_area.text = ""
    assert len(stress_text_area) == 0


def test_next_on_completed_text_raises_stopiteration(stress_text_area):
    stress_text_area.animated = True
    stress_text_area.drawing_text = False

    with pytest.raises(StopIteration):
        next(stress_text_area)


def test_empty_string_animation_state(stress_text_area):
    stress_text_area.animated = True
    stress_text_area.text = "Testing"
    assert stress_text_area.drawing_text is True

    stress_text_area.text = ""
    assert stress_text_area.drawing_text is False
    assert stress_text_area.text == ""
