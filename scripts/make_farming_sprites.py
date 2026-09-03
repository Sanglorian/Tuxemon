#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Draw the placeholder art the planting system needs.

Run from the repository root to regenerate the tilled-soil tiles, the four
plant growth frames and the watering can icon::

    python scripts/make_farming_sprites.py

They are pixel-art placeholders in the game's palette range, meant to be
replaced by real tileset art. Regenerating overwrites the committed PNGs.
"""

from __future__ import annotations

from pathlib import Path

import pygame

TILE = 16
ITEM = 24

GFX = Path(__file__).resolve().parents[1] / "mods" / "tuxemon" / "gfx"
FARMING = GFX / "farming"
ITEMS = GFX / "items"

CLEAR = (0, 0, 0, 0)
SOIL_DRY = (134, 96, 62, 255)
SOIL_DRY_DARK = (108, 76, 48, 255)
SOIL_WET = (86, 60, 38, 255)
SOIL_WET_DARK = (66, 45, 28, 255)
STEM = (74, 132, 58, 255)
LEAF = (108, 178, 78, 255)
LEAF_DARK = (72, 128, 54, 255)
FRUIT = (206, 74, 74, 255)
METAL = (150, 158, 170, 255)
METAL_DARK = (104, 112, 126, 255)
WATER = (86, 152, 210, 255)


def surface(size: tuple[int, int]) -> pygame.Surface:
    s = pygame.Surface(size, pygame.SRCALPHA)
    s.fill(CLEAR)
    return s


def px(
    s: pygame.Surface, x: int, y: int, color: tuple[int, int, int, int]
) -> None:
    if 0 <= x < s.get_width() and 0 <= y < s.get_height():
        s.set_at((x, y), color)


def soil(base: tuple[int, int, int, int], dark: tuple[int, int, int, int]):
    """A tilled tile: flat earth with three ploughed furrows."""
    s = surface((TILE, TILE))
    s.fill(base)
    for row in (3, 8, 13):
        for x in range(1, TILE - 1):
            px(s, x, row, dark)
    for x in (0, TILE - 1):
        for y in range(TILE):
            px(s, x, y, dark)
    return s


def stage0():
    """A single sprout just breaking the surface."""
    s = surface((TILE, TILE))
    for y in (10, 11, 12):
        px(s, 8, y, STEM)
    px(s, 7, 9, LEAF)
    px(s, 9, 9, LEAF)
    return s


def stage1():
    """A seedling with a pair of proper leaves."""
    s = surface((TILE, TILE))
    for y in range(7, 13):
        px(s, 8, y, STEM)
    for x in (5, 6, 7):
        px(s, x, 8, LEAF)
        px(s, x, 9, LEAF_DARK)
    for x in (9, 10, 11):
        px(s, x, 8, LEAF)
        px(s, x, 9, LEAF_DARK)
    px(s, 8, 6, LEAF)
    return s


#: Half-width of the bush canopy at each row, keyed by row.
CANOPY = {4: 2, 5: 3, 6: 4, 7: 4, 8: 4, 9: 3}


def stage2():
    """A grown but barren bush: solid canopy over a short stem."""
    s = surface((TILE, TILE))
    for y in range(9, 14):
        px(s, 8, y, STEM)
    for y, spread in CANOPY.items():
        for x in range(8 - spread, 9 + spread):
            on_edge = (
                x in (8 - spread, 8 + spread)
                or y == min(CANOPY)
                or y == max(CANOPY)
            )
            px(s, x, y, LEAF_DARK if on_edge else LEAF)
    return s


def stage3():
    """The same bush, ripe: three berries showing among the leaves."""
    s = stage2()
    for cx, cy in ((6, 7), (10, 6), (8, 9)):
        for x, y in ((cx, cy), (cx + 1, cy), (cx, cy + 1), (cx + 1, cy + 1)):
            px(s, x, y, FRUIT)
    return s


def watering_can():
    """A 24x24 item icon: a can with a spout and a spray of water."""
    s = surface((ITEM, ITEM))
    for y in range(8, 18):
        for x in range(6, 15):
            px(s, x, y, METAL if (x + y) % 3 else METAL_DARK)
    for x in range(6, 15):
        px(s, x, 7, METAL_DARK)
        px(s, x, 18, METAL_DARK)
    # handle
    for y in range(5, 9):
        px(s, 12, y, METAL_DARK)
    px(s, 11, 4, METAL_DARK)
    px(s, 10, 4, METAL_DARK)
    px(s, 9, 5, METAL_DARK)
    # spout
    for i, y in enumerate(range(9, 15)):
        px(s, 5 - i // 2, y, METAL_DARK)
        px(s, 4 - i // 2, y, METAL)
    # water
    for x, y in ((2, 16), (1, 18), (3, 18), (2, 20), (4, 20)):
        px(s, x, y, WATER)
    return s


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    FARMING.mkdir(parents=True, exist_ok=True)

    outputs = {
        FARMING / "tilled.png": soil(SOIL_DRY, SOIL_DRY_DARK),
        FARMING / "tilled_wet.png": soil(SOIL_WET, SOIL_WET_DARK),
        FARMING / "plant_stage0.png": stage0(),
        FARMING / "plant_stage1.png": stage1(),
        FARMING / "plant_stage2.png": stage2(),
        FARMING / "plant_stage3.png": stage3(),
        ITEMS / "watering_can.png": watering_can(),
    }
    for path, image in outputs.items():
        pygame.image.save(image, str(path))
        print(f"wrote {path.relative_to(GFX.parents[2])}")

    pygame.quit()


if __name__ == "__main__":
    main()
