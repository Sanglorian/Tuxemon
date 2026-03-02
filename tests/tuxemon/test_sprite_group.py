# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pygame
import pytest

from tuxemon.sprite import (
    MenuSpriteGroup,
    RelativeGroup,
    SpriteGroup,
    VisualSpriteList,
)


# Minimal fake sprite for tests
class FakeSprite(pygame.sprite.Sprite):
    def __init__(self, w=10, h=10, enabled=True):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.rect = self.image.get_rect()
        self.enabled = enabled


def test_spritegroup_indexing_and_slicing():
    g = SpriteGroup()
    s1, s2, s3 = FakeSprite(), FakeSprite(), FakeSprite()
    g.add(s1, s2, s3)

    assert g[0] is s1
    assert g[1] is s2
    assert g[-1] is s3
    assert g[0:2] == [s1, s2]


def test_spritegroup_bool():
    g = SpriteGroup()
    assert not g
    g.add(FakeSprite())
    assert g


def test_spritegroup_bounding_rect_single():
    s = FakeSprite()
    s.rect.topleft = (50, 80)
    g = SpriteGroup()
    g.add(s)

    r = g.calc_bounding_rect()
    assert r.topleft == (50, 80)
    assert r.size == s.rect.size


def test_spritegroup_bounding_rect_multiple():
    s1 = FakeSprite()
    s2 = FakeSprite()
    s1.rect.topleft = (0, 0)
    s2.rect.topleft = (100, 50)

    g = SpriteGroup()
    g.add(s1, s2)

    r = g.calc_bounding_rect()
    assert r.left == 0
    assert r.top == 0
    assert r.right == 110
    assert r.bottom == 60


def test_spritegroup_swap():
    g = SpriteGroup()
    s1, s2 = FakeSprite(), FakeSprite()
    g.add(s1)

    g.swap(s1, s2)
    assert s1 not in g.sprites()
    assert s2 in g.sprites()


@pytest.mark.parametrize(
    "button, expected",
    [
        ("LEFT", -1),
        ("RIGHT", 1),
        ("UP", -1),
        ("DOWN", 1),
    ],
)
def test_menuspritegroup_simple_movement(button, expected):
    # Fake button constants
    class E:
        pass

    E.button = getattr(pygame, "K_" + button.lower(), 0)
    E.pressed = True

    g = MenuSpriteGroup()
    for _ in range(5):
        g.add(FakeSprite())

    # Patch movement dict to use our fake key
    g._simple_movement_dict = {E.button: expected}

    new_index = g.determine_cursor_movement(2, E)
    assert new_index == (2 + expected) % 5


def test_menuspritegroup_skips_disabled_items():
    class E:
        pass

    E.button = 1
    E.pressed = True

    g = MenuSpriteGroup()
    s1 = FakeSprite(enabled=True)
    s2 = FakeSprite(enabled=False)
    s3 = FakeSprite(enabled=True)

    g.add(s1, s2, s3)
    g._simple_movement_dict = {1: 1}

    # From index 0 → skip index 1 → land on index 2
    assert g.determine_cursor_movement(0, E) == 2


def test_relativegroup_draw_moves_sprites_temporarily():
    parent = RelativeGroup(parent=lambda: pygame.Rect(100, 200, 300, 300))
    g = RelativeGroup(parent=parent)
    s = FakeSprite()
    g.add(s)

    original_pos = s.rect.topleft
    g.draw(pygame.Surface((800, 600)))

    # After draw, sprite must be restored
    assert s.rect.topleft == original_pos


def test_relativegroup_updates_rect_from_parent_callable():
    g = RelativeGroup(parent=lambda: pygame.Rect(10, 20, 100, 100))
    g.update_rect_from_parent()
    assert g.rect.topleft == (10, 20)


def test_visualsprite_columns_auto_adjust():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 300, 300))
    v = VisualSpriteList(parent=parent)
    v.max_width_per_column = 100

    for _ in range(5):
        v.add(FakeSprite(w=50))

    # Parent rect has NOT been updated → width=0 → columns=1
    v.arrange_menu_items()
    assert v.columns == 1

    # Now update parent rect and arrange again
    parent.update_rect_from_parent()
    v.arrange_menu_items()
    assert v.columns == 3  # 300 // 100


@pytest.mark.parametrize("expand", [True, False])
def test_visualsprite_arrange_spacing(expand):
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 200, 200))
    v = VisualSpriteList(parent=parent)
    v.expand = expand

    for _ in range(4):
        v.add(FakeSprite(h=20))

    v.arrange_menu_items()

    # Check that items are placed in increasing y order
    ys = [s.rect.y for s in v.sprites()]
    assert ys == sorted(ys)


def test_visualsprite_2d_movement_lr_tb_roundtrip():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 300, 300))
    v = VisualSpriteList(parent=parent)
    v.columns = 3

    for _ in range(10):
        v.add(FakeSprite())

    for i in range(len(v)):
        tb = v._lr_to_tb_index(i, "horizontal")
        lr = v._tb_to_lr_index(tb, "horizontal")
        assert lr == i


def test_visualsprite_advance_input_wraparound():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 300, 300))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    v.columns = 3

    for _ in range(7):
        v.add(FakeSprite())

    # Fake DOWN button
    v._2d_movement_dict = {99: ("tb", 1)}

    assert v._advance_input(6, 99) == 1


def test_empty_group_bounding_rect_safe():
    g = SpriteGroup()
    with pytest.raises(IndexError):
        g.calc_bounding_rect()


def test_empty_menu_movement_returns_zero():
    class E:
        pass

    E.button = 1
    E.pressed = True

    g = MenuSpriteGroup()
    assert g.determine_cursor_movement(0, E) == 0


class FakeSprite(pygame.sprite.Sprite):
    def __init__(self, w=10, h=10, enabled=True):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.rect = self.image.get_rect()
        self.enabled = enabled


def test_visualsprite_requires_parent_rect_before_arrange():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 300, 200))
    v = VisualSpriteList(parent=parent)
    v.max_width_per_column = 100

    for _ in range(5):
        v.add(FakeSprite())

    # No parent.update_rect_from_parent() called → width=0
    v.arrange_menu_items()
    assert v.columns == 1


def test_visualsprite_parent_rect_propagation_explicit():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 300, 200))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    v.max_width_per_column = 100

    for _ in range(5):
        v.add(FakeSprite())

    v.arrange_menu_items()
    assert v.columns == 3  # 300 // 100


def test_visualsprite_needs_arrange_lifecycle():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 300, 200))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    assert v._needs_arrange is False

    v.add(FakeSprite())
    assert v._needs_arrange is True

    v.arrange_menu_items()
    assert v._needs_arrange is False

    v.remove(v.sprites()[0])
    assert v._needs_arrange is True


@pytest.mark.parametrize(
    "count, columns",
    [
        (1, 1),
        (2, 1),
        (3, 2),
        (5, 3),
        (7, 3),
        (10, 4),
    ],
)
def test_visualsprite_lr_tb_roundtrip(count, columns):
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 300, 300))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    v.columns = columns

    for _ in range(count):
        v.add(FakeSprite())

    for i in range(len(v)):
        tb = v._lr_to_tb_index(i, "horizontal")
        lr = v._tb_to_lr_index(tb, "horizontal")
        assert lr == i


def test_visualsprite_down_movement_ragged_grid():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 300, 300))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    v.columns = 3

    for _ in range(7):
        v.add(FakeSprite())

    # Fake DOWN button
    v._2d_movement_dict = {99: ("tb", 1)}

    # Expected behavior: LR 6 → TB 2 → TB 3 → LR 1
    assert v._advance_input(6, 99) == 1


def test_visualsprite_layout_stable_after_arrange():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 200, 200))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    for _ in range(6):
        v.add(FakeSprite())

    v.arrange_menu_items()
    first_positions = [s.rect.topleft for s in v.sprites()]

    v.arrange_menu_items()
    second_positions = [s.rect.topleft for s in v.sprites()]

    assert first_positions == second_positions


@pytest.mark.parametrize("expand", [True, False])
def test_visualsprite_spacing_behavior(expand):
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 200, 200))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    v.expand = expand

    for _ in range(4):
        v.add(FakeSprite(h=20))

    v.arrange_menu_items()

    ys = [s.rect.y for s in v.sprites()]
    diffs = [b - a for a, b in zip(ys, ys[1:])]

    if expand:
        # Should be roughly equal spacing across height
        assert max(diffs) - min(diffs) < 5
    else:
        # Should be based on 20 * 1.2 = 24
        assert all(abs(d - 24) < 2 for d in diffs)


def test_visualsprite_draw_restores_rects():
    parent = RelativeGroup(parent=lambda: pygame.Rect(100, 200, 300, 300))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    s = FakeSprite()
    v.add(s)

    original = s.rect.topleft
    v.draw(pygame.Surface((800, 600)))
    assert s.rect.topleft == original


def test_visualsprite_vertical_orientation_layout():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 200, 200))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    v.orientation = "vertical"
    v.columns = 2  # now means "rows" in vertical mode

    for _ in range(4):
        v.add(FakeSprite(w=20, h=20))

    v.arrange_menu_items()

    # In vertical mode:
    # index → (row, col) = divmod(index, rows)
    # so items should move horizontally first
    xs = [s.rect.x for s in v.sprites()]
    assert xs == sorted(xs)


def test_visualsprite_vertical_lr_tb_roundtrip():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 300, 300))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    v.orientation = "vertical"
    v.columns = 3

    for _ in range(10):
        v.add(FakeSprite())

    for i in range(len(v)):
        tb = v._lr_to_tb_index(i, "vertical")
        lr = v._tb_to_lr_index(tb, "vertical")
        assert lr == i


def test_visualsprite_vertical_movement():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 300, 300))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    v.orientation = "vertical"
    v.columns = 2

    for _ in range(6):
        v.add(FakeSprite())

    # Fake RIGHT button (in vertical mode → becomes TB movement)
    v._2d_movement_dict = {99: ("lr", 1)}

    # In vertical mode, LR becomes TB
    # So moving from index 0 should go to index 1
    assert v._advance_input(0, 99) == 1


def test_visualsprite_rectangular_lr_tb_roundtrip():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 300, 300))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    v.rectangular = True
    v.columns = 3

    for _ in range(7):
        v.add(FakeSprite())

    for i in range(len(v)):
        tb = v._lr_to_tb_index(i, "horizontal")
        lr = v._tb_to_lr_index(tb, "horizontal")
        assert lr == i


def test_visualsprite_rectangular_movement_wraparound():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 300, 300))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    v.rectangular = True
    v.columns = 3

    for _ in range(7):
        v.add(FakeSprite())

    # Fake DOWN button
    v._2d_movement_dict = {99: ("tb", 1)}

    # Rectangular grid:
    # 0 1 2
    # 3 4 5
    # 6 7 8 (virtual)
    # DOWN from 6 → 7
    assert v._advance_input(6, 99) == 7 % len(v)


def test_visualsprite_rectangular_layout_stable():
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 200, 200))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    v.rectangular = True
    v.columns = 3

    for _ in range(5):
        v.add(FakeSprite())

    v.arrange_menu_items()
    first = [s.rect.topleft for s in v.sprites()]

    v.arrange_menu_items()
    second = [s.rect.topleft for s in v.sprites()]

    assert first == second


@pytest.mark.parametrize("expand", [True, False])
def test_visualsprite_vertical_spacing(expand):
    parent = RelativeGroup(parent=lambda: pygame.Rect(0, 0, 200, 200))
    parent.update_rect_from_parent()

    v = VisualSpriteList(parent=parent)
    v.orientation = "vertical"
    v.expand = expand

    for _ in range(4):
        v.add(FakeSprite(w=20, h=20))

    v.arrange_menu_items()

    xs = [s.rect.x for s in v.sprites()]
    diffs = [b - a for a, b in zip(xs, xs[1:])]

    if expand:
        assert max(diffs) - min(diffs) < 5
    else:
        assert all(abs(d - 24) < 2 for d in diffs)
